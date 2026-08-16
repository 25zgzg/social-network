from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib.auth import login
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .forms import CommentForm, ConversationForm, GroupForm, MessageForm, NotificationSettingForm, PostForm, ProfileForm, RatingForm, SignupForm
from .models import Conversation, Event, Follow, Friendship, Group, Like, Membership, Message, NotificationSetting, Post, Profile, Rating, create_notification, message_payload, notify_message

def visible_posts(user):
    """Пости видимі користувачу: власні, друзів (accepted), підписок та спільнот, де він учасник."""
    pairs=Friendship.objects.filter(Q(sender=user,status='accepted')|Q(receiver=user,status='accepted')).values_list('sender_id','receiver_id')
    ids={user.id}; [ids.update(pair) for pair in pairs]
    followed=Follow.objects.filter(follower=user).values_list('target_id',flat=True)
    return Post.objects.filter(Q(author_id__in=ids|set(followed))|Q(group__members=user)).distinct()
def home(request):
    qs=visible_posts(request.user) if request.user.is_authenticated else Post.objects.all()
    posts=qs.select_related('author','group','shared_from__author','shared_from__group').annotate(like_count=Count('likes'))[:30]
    popular_users=User.objects.annotate(follower_count=Count('followers')).order_by('-follower_count')[:5]
    return render(request,'network/home.html',{'posts':posts,'groups':Group.objects.annotate(member_count=Count('members')).order_by('-member_count')[:5],'popular_users':popular_users,'upcoming_events':Event.objects.filter(starts_at__gte=timezone.now())[:5]})
def signup(request):
    form=SignupForm(request.POST or None)
    if form.is_valid():
        user=form.save(); Profile.objects.create(user=user); login(request,user,backend='django.contrib.auth.backends.ModelBackend'); return redirect('home')
    return render(request,'registration/signup.html',{'form':form})
@login_required
def feed(request):
    form=PostForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        p=form.save(commit=False); p.author=request.user; p.save(); return redirect('feed')
    posts=visible_posts(request.user).select_related('author','group','shared_from__author','shared_from__group')
    return render(request,'network/feed.html',{'posts':posts,'form':form})
@login_required
def profile(request,username):
    user=get_object_or_404(User,username=username); Profile.objects.get_or_create(user=user)
    fs=Friendship.objects.filter(Q(sender=request.user,receiver=user)|Q(sender=user,receiver=request.user)).first()
    state='friend' if fs and fs.status=='accepted' else 'incoming' if fs and fs.sender==user else 'outgoing' if fs else 'none'
    return render(request,'network/profile.html',{'profile_user':user,'profile':user.profile,'posts':user.posts.all(),'is_following':Follow.objects.filter(follower=request.user,target=user).exists(),'friend_state':state})
@login_required
def edit_profile(request):
    profile,_=Profile.objects.get_or_create(user=request.user); form=ProfileForm(request.POST or None,instance=profile)
    if form.is_valid(): form.save(); return redirect('profile',request.user.username)
    return render(request,'network/form.html',{'form':form,'title':'Редагування профілю'})
@login_required
@require_POST
def toggle_like(request,pk):
    post=get_object_or_404(Post,pk=pk); like,created=Like.objects.get_or_create(user=request.user,post=post)
    if not created: like.delete()
    elif post.author!=request.user: create_notification(post.author,request.user,f'{request.user.username} вподобав вашу публікацію',kind='like')
    return redirect(request.META.get('HTTP_REFERER','feed'))
@login_required
@require_POST
def add_comment(request,pk):
    post=get_object_or_404(Post,pk=pk); form=CommentForm(request.POST)
    if form.is_valid():
        c=form.save(commit=False); c.post=post; c.user=request.user; c.save()
        if post.author!=request.user: create_notification(post.author,request.user,f'{request.user.username} прокоментував вашу публікацію',kind='comment')
    return redirect(request.META.get('HTTP_REFERER','feed'))
@login_required
@require_POST
def share_post(request,pk):
    original=get_object_or_404(Post,pk=pk)
    if original.shared_from: original=original.shared_from
    Post.objects.create(author=request.user,shared_from=original,body=request.POST.get('body',''))
    if original.author!=request.user: create_notification(original.author,request.user,f'{request.user.username} поширив вашу публікацію',kind='like')
    return redirect(request.META.get('HTTP_REFERER','feed'))
@login_required
@require_POST
def rate_post(request,pk):
    """Оцінка публікації 1-5 з необов'язковим відгуком; повторне надсилання оновлює існуючий запис."""
    post=get_object_or_404(Post,pk=pk); form=RatingForm(request.POST)
    if form.is_valid():
        rating,created=Rating.objects.get_or_create(user=request.user,post=post,defaults={'value':form.cleaned_data['value'],'review':form.cleaned_data['review']})
        if not created: rating.value=form.cleaned_data['value'];rating.review=form.cleaned_data['review'];rating.save()
    return redirect(request.META.get('HTTP_REFERER','feed'))
@login_required
@require_POST
def follow(request,username):
    target=get_object_or_404(User,username=username)
    if target!=request.user:
        obj,created=Follow.objects.get_or_create(follower=request.user,target=target)
        if created: create_notification(target,request.user,f'@{request.user.username} підписався на вас',f'/u/{request.user.username}/',kind='follow')
        else: obj.delete()
    return redirect('profile',username)
def _is_group_admin(user,group):
    return group.owner_id==user.id or Membership.objects.filter(group=group,user=user,is_admin=True).exists()
@login_required
def create_group(request):
    form=GroupForm(request.POST or None)
    if form.is_valid():
        g=form.save(commit=False); g.owner=request.user; g.save(); Membership.objects.create(user=request.user,group=g,is_admin=True); return redirect('group_detail',g.pk)
    return render(request,'network/form.html',{'form':form,'title':'Нова спільнота'})
@login_required
def groups_list(request):
    q=request.GET.get('q','').strip()
    groups=Group.objects.annotate(member_count=Count('members',distinct=True),post_count=Count('posts',distinct=True)).order_by('name')
    if q: groups=groups.filter(name__icontains=q)
    return render(request,'network/groups.html',{'groups':groups,'q':q})
@login_required
def group_detail(request,pk):
    group=get_object_or_404(Group,pk=pk); membership=Membership.objects.filter(group=group,user=request.user).first(); member=membership is not None; form=PostForm(request.POST or None)
    is_owner=group.owner_id==request.user.id; group_admin=is_owner or bool(membership and membership.is_admin)
    if request.method=='POST' and member and form.is_valid():
        p=form.save(commit=False); p.author=request.user; p.group=group; p.save(); return redirect('group_detail',pk)
    memberships=group.membership_set.select_related('user').order_by('-is_admin','user__username')
    return render(request,'network/group.html',{'group':group,'member':member,'is_owner':is_owner,'group_admin':group_admin,'memberships':memberships,'posts':group.posts.select_related('author'),'form':form})
@login_required
@require_POST
def join_group(request,pk):
    group=get_object_or_404(Group,pk=pk); Membership.objects.get_or_create(user=request.user,group=group); return redirect('group_detail',pk)
@login_required
@require_POST
def leave_group(request,pk):
    group=get_object_or_404(Group,pk=pk)
    if group.owner_id==request.user.id:
        messages.error(request,'Власник не може покинути власну групу.'); return redirect('group_detail',pk)
    Membership.objects.filter(group=group,user=request.user).delete(); return redirect('group_detail',pk)
@login_required
@require_POST
def group_delete_post(request,pk,post_pk):
    group=get_object_or_404(Group,pk=pk); post=get_object_or_404(Post,pk=post_pk,group=group)
    if not (_is_group_admin(request.user,group) or post.author_id==request.user.id): raise Http404
    post.delete(); return redirect('group_detail',pk)
@login_required
@require_POST
def group_kick_member(request,pk,user_id):
    group=get_object_or_404(Group,pk=pk)
    if not _is_group_admin(request.user,group): raise Http404
    target=get_object_or_404(User,pk=user_id)
    if target.id==group.owner_id or (Membership.objects.filter(group=group,user=target,is_admin=True).exists() and request.user.id!=group.owner_id): raise Http404
    Membership.objects.filter(group=group,user=target).delete(); return redirect('group_detail',pk)
@login_required
@require_POST
def group_toggle_admin(request,pk,user_id):
    group=get_object_or_404(Group,pk=pk)
    if group.owner_id!=request.user.id: raise Http404
    membership=get_object_or_404(Membership,group=group,user_id=user_id)
    membership.is_admin=not membership.is_admin; membership.save(update_fields=['is_admin']); return redirect('group_detail',pk)
@login_required
@require_POST
def rate_group(request,pk):
    """Оцінка групи 1-5 з необов'язковим відгуком; повторне надсилання оновлює існуючий запис."""
    group=get_object_or_404(Group,pk=pk); form=RatingForm(request.POST)
    if form.is_valid():
        rating,created=Rating.objects.get_or_create(user=request.user,group=group,defaults={'value':form.cleaned_data['value'],'review':form.cleaned_data['review']})
        if not created: rating.value=form.cleaned_data['value'];rating.review=form.cleaned_data['review'];rating.save()
    return redirect(request.META.get('HTTP_REFERER','feed'))
@login_required
@require_POST
def rating_hide(request,pk):
    """Модерація: лише staff ховає відгук із стрічки та середніх оцінок."""
    if not request.user.is_staff: raise Http404
    rating=get_object_or_404(Rating,pk=pk); rating.is_approved=False; rating.save(update_fields=['is_approved'])
    return redirect(request.META.get('HTTP_REFERER','feed'))
@login_required
@require_POST
def rating_restore(request,pk):
    """Модерація: лише staff повертає прихований відгук."""
    if not request.user.is_staff: raise Http404
    rating=get_object_or_404(Rating,pk=pk); rating.is_approved=True; rating.save(update_fields=['is_approved'])
    return redirect(request.META.get('HTTP_REFERER','feed'))
@login_required
def notifications(request):
    items=request.user.notifications.order_by('-created_at'); items.update(is_read=True); return render(request,'network/notifications.html',{'items':items})
@login_required
def notification_settings(request):
    setting,_=NotificationSetting.objects.get_or_create(user=request.user); form=NotificationSettingForm(request.POST or None,instance=setting)
    if form.is_valid(): form.save(); return redirect('notifications')
    return render(request,'network/notification_settings.html',{'form':form,'title':'Налаштування сповіщень'})
@login_required
def chats(request):
    return render(request,'network/chats.html',{'conversations':request.user.conversations.all()})
@login_required
def conversation(request,pk):
    chat=get_object_or_404(Conversation.objects.filter(participants=request.user),pk=pk); form=MessageForm(request.POST or None)
    if form.is_valid(): m=form.save(commit=False);m.sender=request.user;m.conversation=chat;m.save();notify_message(m);return redirect('conversation',pk)
    return render(request,'network/conversation.html',{'chat':chat,'form':form})
@login_required
def conversation_create(request):
    friends=User.objects.filter(Q(received_friendships__sender=request.user,received_friendships__status='accepted')|Q(sent_friendships__receiver=request.user,sent_friendships__status='accepted')).exclude(pk=request.user.pk).distinct()
    form=ConversationForm(request.POST or None); form.fields['participants'].queryset=friends
    if form.is_valid():
        c=Conversation.objects.create(title=form.cleaned_data['title']); c.participants.add(request.user,*form.cleaned_data['participants']); return redirect('conversation',c.pk)
    return render(request,'network/form.html',{'form':form,'title':'Новий чат'})
@login_required
@require_POST
def chat_upload(request,pk):
    chat=get_object_or_404(Conversation.objects.filter(participants=request.user),pk=pk); file=request.FILES.get('attachment')
    if file:
        m=Message.objects.create(conversation=chat,sender=request.user,body=request.POST.get('body',''),attachment=file); notify_message(m)
        async_to_sync(get_channel_layer().group_send)(f'chat_{chat.pk}',{'type':'chat.message','message':message_payload(m)})
    return redirect('conversation',pk)
@login_required
def friend_requests(request):
    incoming=request.user.received_friendships.filter(status='pending').select_related('sender')
    outgoing=request.user.sent_friendships.filter(status='pending').select_related('receiver')
    accepted=Friendship.objects.filter(Q(sender=request.user,status='accepted')|Q(receiver=request.user,status='accepted')).select_related('sender','receiver')
    friends=[(f.receiver if f.sender==request.user else f.sender) for f in accepted]
    return render(request,'network/friends.html',{'incoming':incoming,'outgoing':outgoing,'friends':friends})
@login_required
@require_POST
def friend_action(request,username):
    target=get_object_or_404(User,username=username); action=request.POST.get('action') or 'send'; incoming=Friendship.objects.filter(sender=target,receiver=request.user).first(); outgoing=Friendship.objects.filter(sender=request.user,receiver=target).first()
    if action in('accept','send') and incoming and incoming.status=='pending':
        incoming.status='accepted';incoming.save();create_notification(target,request.user,f'@{request.user.username} прийняв ваш запит у друзі',f'/u/{request.user.username}/',kind='friend')
    elif action=='reject': Friendship.objects.filter(sender=target,receiver=request.user,status='pending').delete()
    elif action=='cancel': Friendship.objects.filter(sender=request.user,receiver=target,status='pending').delete()
    elif action=='remove': Friendship.objects.filter(Q(sender=request.user,receiver=target)|Q(sender=target,receiver=request.user),status='accepted').delete()
    elif action=='send' and target!=request.user and not incoming and not outgoing:
        Friendship.objects.create(sender=request.user,receiver=target);create_notification(target,request.user,f'@{request.user.username} надіслав вам запит у друзі','/friends/',kind='friend')
    return redirect(request.META.get('HTTP_REFERER') or f'/u/{username}/')

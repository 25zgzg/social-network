from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.contrib.auth import login
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .forms import CommentForm, ConversationForm, GroupForm, MessageForm, PostForm, ProfileForm, RatingForm, SignupForm
from .models import Conversation, Follow, Friendship, Group, Like, Membership, Message, Notification, Post, Profile, Rating, message_payload, notify_message

def home(request):
    posts=Post.objects.select_related('author','group').annotate(like_count=Count('likes'))[:30]
    return render(request,'network/home.html',{'posts':posts,'groups':Group.objects.annotate(member_count=Count('members')).order_by('-member_count')[:5]})
def signup(request):
    form=SignupForm(request.POST or None)
    if form.is_valid():
        user=form.save(); Profile.objects.create(user=user); login(request,user); return redirect('home')
    return render(request,'registration/signup.html',{'form':form})
@login_required
def feed(request):
    form=PostForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        p=form.save(commit=False); p.author=request.user; p.save(); return redirect('feed')
    pairs=Friendship.objects.filter(Q(sender=request.user,status='accepted')|Q(receiver=request.user,status='accepted')).values_list('sender_id','receiver_id')
    ids={request.user.id}; [ids.update(pair) for pair in pairs]
    followed=Follow.objects.filter(follower=request.user).values_list('target_id',flat=True)
    posts=Post.objects.filter(Q(author_id__in=ids|set(followed))|Q(group__members=request.user)).distinct()
    return render(request,'network/feed.html',{'posts':posts,'form':form})
@login_required
def profile(request,username):
    user=get_object_or_404(User,username=username); Profile.objects.get_or_create(user=user)
    return render(request,'network/profile.html',{'profile_user':user,'profile':user.profile,'posts':user.posts.all(),'is_following':Follow.objects.filter(follower=request.user,target=user).exists()})
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
    elif post.author!=request.user: Notification.objects.create(recipient=post.author,actor=request.user,text=f'{request.user.username} вподобав вашу публікацію')
    return redirect(request.META.get('HTTP_REFERER','feed'))
@login_required
@require_POST
def add_comment(request,pk):
    post=get_object_or_404(Post,pk=pk); form=CommentForm(request.POST)
    if form.is_valid():
        c=form.save(commit=False); c.post=post; c.user=request.user; c.save()
        if post.author!=request.user: Notification.objects.create(recipient=post.author,actor=request.user,text=f'{request.user.username} прокоментував вашу публікацію')
    return redirect(request.META.get('HTTP_REFERER','feed'))
@login_required
@require_POST
def follow(request,username):
    target=get_object_or_404(User,username=username)
    if target!=request.user:
        obj,created=Follow.objects.get_or_create(follower=request.user,target=target)
        if not created: obj.delete()
    return redirect('profile',username)
@login_required
def create_group(request):
    form=GroupForm(request.POST or None)
    if form.is_valid():
        g=form.save(commit=False); g.owner=request.user; g.save(); Membership.objects.create(user=request.user,group=g,is_admin=True); return redirect('group_detail',g.pk)
    return render(request,'network/form.html',{'form':form,'title':'Нова спільнота'})
@login_required
def group_detail(request,pk):
    group=get_object_or_404(Group,pk=pk); member=Membership.objects.filter(group=group,user=request.user).exists(); form=PostForm(request.POST or None)
    if request.method=='POST' and member and form.is_valid():
        p=form.save(commit=False); p.author=request.user; p.group=group; p.save(); return redirect('group_detail',pk)
    return render(request,'network/group.html',{'group':group,'member':member,'posts':group.posts.all(),'form':form})
@login_required
@require_POST
def join_group(request,pk):
    group=get_object_or_404(Group,pk=pk); Membership.objects.get_or_create(user=request.user,group=group); return redirect('group_detail',pk)
@login_required
def notifications(request):
    items=request.user.notifications.order_by('-created_at'); items.update(is_read=True); return render(request,'network/notifications.html',{'items':items})
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
    return render(request,'network/friends.html',{'requests':request.user.received_friendships.filter(status='pending')})
@login_required
@require_POST
def friend_action(request,username):
    target=get_object_or_404(User,username=username); pending=Friendship.objects.filter(sender=target,receiver=request.user,status='pending').first()
    if pending: pending.status='accepted';pending.save()
    elif target!=request.user: Friendship.objects.get_or_create(sender=request.user,receiver=target)
    return redirect('profile',username)

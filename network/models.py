import re
from django.conf import settings
from django.db import models
from django.db.models import Avg, Count
from django.urls import reverse

User = settings.AUTH_USER_MODEL

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    avatar = models.URLField(blank=True)
    cover = models.URLField(blank=True)
    def __str__(self): return self.user.username

class Friendship(models.Model):
    PENDING='pending'; ACCEPTED='accepted'; STATUS=[(PENDING,'Очікує'),(ACCEPTED,'Прийнято')]
    sender=models.ForeignKey(User,on_delete=models.CASCADE,related_name='sent_friendships')
    receiver=models.ForeignKey(User,on_delete=models.CASCADE,related_name='received_friendships')
    status=models.CharField(max_length=10,choices=STATUS,default=PENDING)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['sender','receiver'],name='unique_friend_request')]

class Follow(models.Model):
    follower=models.ForeignKey(User,on_delete=models.CASCADE,related_name='following')
    target=models.ForeignKey(User,on_delete=models.CASCADE,related_name='followers')
    class Meta: constraints=[models.UniqueConstraint(fields=['follower','target'],name='unique_follow')]

class Group(models.Model):
    name=models.CharField(max_length=120); description=models.TextField(); owner=models.ForeignKey(User,on_delete=models.CASCADE,related_name='owned_groups'); members=models.ManyToManyField(User,through='Membership',related_name='social_groups'); created_at=models.DateTimeField(auto_now_add=True)
    def get_absolute_url(self): return reverse('group_detail',args=[self.pk])
    @property
    def rating_stats(self): return rating_stats(self.ratings)
class Membership(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE); group=models.ForeignKey(Group,on_delete=models.CASCADE); is_admin=models.BooleanField(default=False); joined_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['user','group'],name='unique_membership')]

class Post(models.Model):
    author=models.ForeignKey(User,on_delete=models.CASCADE,related_name='posts'); group=models.ForeignKey(Group,on_delete=models.CASCADE,null=True,blank=True,related_name='posts'); body=models.TextField(); media_url=models.URLField(blank=True); shared_from=models.ForeignKey('self',null=True,blank=True,on_delete=models.CASCADE,related_name='shares'); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=['-created_at']
    @property
    def media_kind(self):
        u=self.media_url
        if not u: return ''
        if self.youtube_embed_url: return 'youtube'
        u=u.lower()
        if u.endswith(('.png','.jpg','.jpeg','.gif','.webp')): return 'image'
        if u.endswith(('.mp4','.webm','.ogg')): return 'video'
        return 'link'
    @property
    def youtube_embed_url(self):
        m=re.search(r'(?:youtube\.com/(?:watch\?.*?v=|shorts/)|youtu\.be/)([\w-]{11})',self.media_url)
        return f'https://www.youtube.com/embed/{m.group(1)}' if m else ''
    @property
    def rating_stats(self): return rating_stats(self.ratings)
class Like(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE); post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name='likes')
    class Meta: constraints=[models.UniqueConstraint(fields=['user','post'],name='unique_like')]
class Comment(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE); post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name='comments'); body=models.TextField(); created_at=models.DateTimeField(auto_now_add=True)
class Notification(models.Model):
    recipient=models.ForeignKey(User,on_delete=models.CASCADE,related_name='notifications'); actor=models.ForeignKey(User,on_delete=models.CASCADE); text=models.CharField(max_length=255); url=models.CharField(max_length=255,blank=True); is_read=models.BooleanField(default=False); created_at=models.DateTimeField(auto_now_add=True)
class Conversation(models.Model):
    title=models.CharField(max_length=120,blank=True); participants=models.ManyToManyField(User,related_name='conversations'); created_at=models.DateTimeField(auto_now_add=True)
class Message(models.Model):
    conversation=models.ForeignKey(Conversation,on_delete=models.CASCADE,related_name='messages'); sender=models.ForeignKey(User,on_delete=models.CASCADE); body=models.TextField(blank=True); attachment=models.FileField(upload_to='chat/%Y/%m/',blank=True); created_at=models.DateTimeField(auto_now_add=True)
    @property
    def is_image(self):
        return bool(self.attachment) and self.attachment.name.lower().endswith(('.png','.jpg','.jpeg','.gif','.webp'))
    @property
    def attachment_name(self):
        return self.attachment.name.rsplit('/',1)[-1] if self.attachment else ''

def notify_message(message):
    """Створює сповіщення всім іншим учасникам розмови про нове повідомлення."""
    text=f'{message.sender.username}: {(message.body or message.attachment_name)[:80]}'
    for user in message.conversation.participants.exclude(pk=message.sender.pk):
        Notification.objects.create(recipient=user,actor=message.sender,text=text[:255],url=f'/chats/{message.conversation.pk}/')

def message_payload(message):
    """Єдиний формат повідомлення для WebSocket-розсилки (consumer + upload view)."""
    data={'id':message.pk,'sender':message.sender.username,'body':message.body,'created_at':message.created_at.strftime('%H:%M')}
    if message.attachment: data['attachment']={'url':message.attachment.url,'name':message.attachment_name}
    return data
class Rating(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE); post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name='ratings',null=True,blank=True); group=models.ForeignKey(Group,on_delete=models.CASCADE,related_name='ratings',null=True,blank=True); value=models.PositiveSmallIntegerField(); review=models.TextField(blank=True); is_approved=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True)
def rating_stats(ratings):
    """(середня оцінка, кількість) лише зі схвалених відгуків (is_approved=True)."""
    agg=ratings.filter(is_approved=True).aggregate(avg=Avg('value'),count=Count('id'))
    return agg['avg'] or 0,agg['count']

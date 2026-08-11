from django.conf import settings
from django.db import models
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
class Membership(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE); group=models.ForeignKey(Group,on_delete=models.CASCADE); is_admin=models.BooleanField(default=False); joined_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['user','group'],name='unique_membership')]

class Post(models.Model):
    author=models.ForeignKey(User,on_delete=models.CASCADE,related_name='posts'); group=models.ForeignKey(Group,on_delete=models.CASCADE,null=True,blank=True,related_name='posts'); body=models.TextField(); media_url=models.URLField(blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=['-created_at']
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
    conversation=models.ForeignKey(Conversation,on_delete=models.CASCADE,related_name='messages'); sender=models.ForeignKey(User,on_delete=models.CASCADE); body=models.TextField(); created_at=models.DateTimeField(auto_now_add=True)
class Rating(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE); post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name='ratings',null=True,blank=True); group=models.ForeignKey(Group,on_delete=models.CASCADE,related_name='ratings',null=True,blank=True); value=models.PositiveSmallIntegerField(); review=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True)

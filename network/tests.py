from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import Conversation, Friendship, Group, Membership, Post, Profile
class SocialTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
 def test_feed_creates_post(self):
  self.client.post(reverse('feed'),{'body':'Привіт, мереже!','media_url':''});self.assertTrue(Post.objects.filter(body='Привіт, мереже!').exists())
 def test_group_members_can_post(self):
  g=Group.objects.create(name='Python',description='Dev',owner=self.user);Membership.objects.create(group=g,user=self.user,is_admin=True)
  self.client.post(reverse('group_detail',args=[g.pk]),{'body':'Django','media_url':''});self.assertEqual(g.posts.count(),1)
 def test_anonymous_feed_redirects(self):
  self.client.logout();self.assertEqual(self.client.get(reverse('feed')).status_code,302)
 def test_login_page_shows_google_button(self):
  self.client.logout();r=self.client.get('/accounts/login/')
  self.assertEqual(r.status_code,200);self.assertIn('google',r.content.decode().lower())
 def test_google_adapter_creates_profile(self):
  from .adapters import CustomSocialAccountAdapter
  from allauth.socialaccount.models import SocialAccount, SocialLogin
  from django.contrib.auth.models import User as U
  user=U.objects.create_user('guser',password='strong-pass-123')
  acc=SocialAccount(user=user,provider='google',extra_data={'picture':'https://lh3.googleusercontent.com/x.png'})
  CustomSocialAccountAdapter().setup_profile(SocialLogin(account=acc,user=user))
  self.assertEqual(user.profile.avatar,'https://lh3.googleusercontent.com/x.png')

@override_settings(CHANNEL_LAYERS={'default':{'BACKEND':'channels.layers.InMemoryChannelLayer'}})
class ChatTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
  self.other=User.objects.create_user('olia',password='strong-pass-123');Profile.objects.create(user=self.other)
  Friendship.objects.create(sender=self.user,receiver=self.other,status='accepted')
 def test_conversation_create_with_friends(self):
  self.client.post(reverse('conversation_create'),{'title':'','participants':[self.other.pk]})
  conv=Conversation.objects.first();self.assertIsNotNone(conv)
  self.assertIn(self.user,conv.participants.all());self.assertIn(self.other,conv.participants.all())
 def test_conversation_denied_for_non_participant(self):
  stranger=User.objects.create_user('stranger',password='strong-pass-123');Profile.objects.create(user=stranger)
  conv=Conversation.objects.create();conv.participants.add(self.other)
  self.client.logout();self.client.login(username='stranger',password='strong-pass-123')
  self.assertEqual(self.client.get(reverse('conversation',args=[conv.pk])).status_code,404)
  f=SimpleUploadedFile('x.txt',b'x',content_type='text/plain')
  self.assertEqual(self.client.post(reverse('chat_upload',args=[conv.pk]),{'attachment':f}).status_code,404)
 def test_chat_upload_creates_message_and_notification(self):
  conv=Conversation.objects.create();conv.participants.add(self.user,self.other)
  f=SimpleUploadedFile('note.txt',b'hello',content_type='text/plain')
  self.client.post(reverse('chat_upload',args=[conv.pk]),{'attachment':f,'body':'Ось файл'})
  m=conv.messages.first();self.assertIsNotNone(m);self.assertTrue(bool(m.attachment));self.assertEqual(m.body,'Ось файл')
  self.assertEqual(self.other.notifications.count(),1);self.assertEqual(self.user.notifications.count(),0)
 def test_conversation_post_fallback_notifies(self):
  conv=Conversation.objects.create();conv.participants.add(self.user,self.other)
  self.client.post(reverse('conversation',args=[conv.pk]),{'body':'Привіт!'})
  self.assertTrue(conv.messages.filter(body='Привіт!').exists());self.assertEqual(self.other.notifications.count(),1)

class FriendshipTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
  self.other=User.objects.create_user('olia',password='strong-pass-123');Profile.objects.create(user=self.other)
 def test_reject_deletes_incoming_request(self):
  Friendship.objects.create(sender=self.other,receiver=self.user)
  self.client.post(reverse('friend_action',args=['olia']),{'action':'reject'});self.assertFalse(Friendship.objects.exists())
 def test_cancel_removes_outgoing_request(self):
  Friendship.objects.create(sender=self.user,receiver=self.other)
  self.client.post(reverse('friend_action',args=['olia']),{'action':'cancel'});self.assertFalse(Friendship.objects.exists())
 def test_remove_unfriends_both_directions(self):
  Friendship.objects.create(sender=self.other,receiver=self.user,status='accepted');self.client.post(reverse('friend_action',args=['olia']),{'action':'remove'});self.assertFalse(Friendship.objects.exists())
  Friendship.objects.create(sender=self.user,receiver=self.other,status='accepted');self.client.post(reverse('friend_action',args=['olia']),{'action':'remove'});self.assertFalse(Friendship.objects.exists())
 def test_friends_page_lists_accepted_friend(self):
  Friendship.objects.create(sender=self.other,receiver=self.user,status='accepted')
  r=self.client.get(reverse('friends'));self.assertContains(r,'@olia')
 def test_request_and_accept_create_notifications(self):
  self.client.post(reverse('friend_action',args=['olia']),{'action':'send'})
  self.assertEqual(self.other.notifications.count(),1);self.assertIn('запит у друзі',self.other.notifications.first().text);self.assertEqual(self.other.notifications.first().url,'/friends/')
  self.client.logout();self.client.login(username='olia',password='strong-pass-123');self.client.post(reverse('friend_action',args=['nazar']),{'action':'accept'})
  self.assertTrue(Friendship.objects.filter(status='accepted').exists());self.assertEqual(self.user.notifications.count(),1);self.assertIn('прийняв',self.user.notifications.first().text)
 def test_follow_notifies_only_on_create(self):
  self.client.post(reverse('follow',args=['olia']));self.assertEqual(self.other.notifications.count(),1);self.assertIn('підписався',self.other.notifications.first().text)
  self.client.post(reverse('follow',args=['olia']));self.assertEqual(self.other.notifications.count(),1)

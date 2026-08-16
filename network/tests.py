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

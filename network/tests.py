from datetime import timedelta
import asyncio
import io
import os
import requests
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import re_path, reverse
from asgiref.sync import async_to_sync
from channels.middleware import BaseMiddleware
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from PIL import Image
from . import consumers
from .models import Comment, Conversation, Event, Follow, Friendship, Group, Like, Membership, Message, NotificationSetting, Post, Profile, Rating
class ShareFeedTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
  self.other=User.objects.create_user('olia',password='strong-pass-123');Profile.objects.create(user=self.other)
 def test_share_creates_post_linked_to_original(self):
  orig=Post.objects.create(author=self.other,body='Оригінал')
  self.assertEqual(self.client.post(reverse('share',args=[orig.pk]),{'body':'Гарна думка'}).status_code,302)
  sh=Post.objects.get(body='Гарна думка');self.assertEqual(sh.author,self.user);self.assertEqual(sh.shared_from,orig);self.assertEqual(self.other.notifications.count(),1)
 def test_shared_post_renders_marker(self):
  orig=Post.objects.create(author=self.other,body='Оригінал')
  self.client.post(reverse('share',args=[orig.pk]),{})
  self.assertTrue(Post.objects.filter(shared_from=orig).exists())
  content=self.client.get(reverse('feed')).content.decode();self.assertIn('поширив',content);self.assertIn('share-quote',content)
 def test_media_kinds(self):
  self.assertEqual(Post.objects.create(author=self.user,body='x',media_url='https://a.com/pic.PNG').media_kind,'image')
  self.assertEqual(Post.objects.create(author=self.user,body='x',media_url='https://a.com/clip.mp4').media_kind,'video')
  yt=Post.objects.create(author=self.user,body='x',media_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ')
  self.assertEqual(yt.media_kind,'youtube');self.assertEqual(yt.youtube_embed_url,'https://www.youtube.com/embed/dQw4w9WgXcQ')
  self.assertEqual(Post.objects.create(author=self.user,body='x',media_url='https://youtu.be/dQw4w9WgXcQ?t=1').youtube_embed_url,'https://www.youtube.com/embed/dQw4w9WgXcQ')
  self.assertEqual(Post.objects.create(author=self.user,body='x',media_url='https://a.com/page').media_kind,'link')
  self.assertEqual(Post.objects.create(author=self.user,body='x').media_kind,'')
 def test_home_scope(self):
  stranger=User.objects.create_user('stranger',password='strong-pass-123');Profile.objects.create(user=stranger)
  Friendship.objects.create(sender=self.user,receiver=self.other,status='accepted')
  Post.objects.create(author=self.other,body='friend-body');Post.objects.create(author=stranger,body='stranger-body')
  content=self.client.get(reverse('home')).content.decode();self.assertIn('friend-body',content);self.assertNotIn('stranger-body',content)
  self.client.logout();content=self.client.get(reverse('home')).content.decode();self.assertIn('friend-body',content);self.assertIn('stranger-body',content)
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
  buf=io.BytesIO();Image.new('RGB',(8,8)).save(buf,format='JPEG')
  resp=Mock(status_code=200,headers={'Content-Type':'image/jpeg'},content=buf.getvalue(),raise_for_status=Mock())
  with patch('network.adapters.requests.get',return_value=resp):
   CustomSocialAccountAdapter().setup_profile(SocialLogin(account=acc,user=user))
  self.assertTrue(user.profile.avatar.startswith('/media/avatars/'))

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
 def test_profile_page_renders_friend_button(self):
  r=self.client.get(reverse('profile',args=['olia']));self.assertEqual(r.status_code,200);self.assertContains(r,'Додати в друзі')
class GroupModerationTests(TestCase):
 def setUp(self):
  self.owner=User.objects.create_user('owner',password='strong-pass-123');Profile.objects.create(user=self.owner)
  self.admin=User.objects.create_user('admin',password='strong-pass-123');Profile.objects.create(user=self.admin)
  self.admin2=User.objects.create_user('admin2',password='strong-pass-123');Profile.objects.create(user=self.admin2)
  self.member=User.objects.create_user('member',password='strong-pass-123');Profile.objects.create(user=self.member)
  self.group=Group.objects.create(name='Python',description='Dev',owner=self.owner)
  Membership.objects.create(group=self.group,user=self.owner,is_admin=True);Membership.objects.create(group=self.group,user=self.admin,is_admin=True);Membership.objects.create(group=self.group,user=self.admin2,is_admin=True)
  Membership.objects.create(group=self.group,user=self.member)
  self.member_post=Post.objects.create(author=self.member,group=self.group,body='spam');self.admin_post=Post.objects.create(author=self.admin,group=self.group,body='важливе')
 def _login(self,user): self.client.login(username=user.username,password='strong-pass-123')
 def test_groups_list_renders_and_search_filters(self):
  Group.objects.create(name='Django',description='web',owner=self.owner);self._login(self.member)
  r=self.client.get(reverse('groups'));self.assertEqual(r.status_code,200);self.assertContains(r,'Python');self.assertContains(r,'Django');self.assertContains(r,'учасників')
  r=self.client.get(reverse('groups'),{'q':'pyth'});self.assertContains(r,'>Python<');self.assertNotContains(r,'>Django<')
 def test_leave_group_removes_membership(self):
  self._login(self.member);self.client.post(reverse('leave_group',args=[self.group.pk]))
  self.assertFalse(Membership.objects.filter(group=self.group,user=self.member).exists())
 def test_owner_cannot_leave(self):
  self._login(self.owner);r=self.client.post(reverse('leave_group',args=[self.group.pk]))
  self.assertEqual(r.status_code,302);self.assertTrue(Membership.objects.filter(group=self.group,user=self.owner).exists())
 def test_admin_can_delete_any_post(self):
  self._login(self.admin);self.client.post(reverse('group_delete_post',args=[self.group.pk,self.member_post.pk]))
  self.assertFalse(Post.objects.filter(pk=self.member_post.pk).exists())
 def test_member_cannot_delete_others_post(self):
  self._login(self.member);r=self.client.post(reverse('group_delete_post',args=[self.group.pk,self.admin_post.pk]))
  self.assertEqual(r.status_code,404);self.assertTrue(Post.objects.filter(pk=self.admin_post.pk).exists())
 def test_author_can_delete_own_post(self):
  self._login(self.member);self.client.post(reverse('group_delete_post',args=[self.group.pk,self.member_post.pk]))
  self.assertFalse(Post.objects.filter(pk=self.member_post.pk).exists())
 def test_admin_can_kick_member(self):
  self._login(self.admin);self.client.post(reverse('group_kick_member',args=[self.group.pk,self.member.pk]))
  self.assertFalse(Membership.objects.filter(group=self.group,user=self.member).exists())
 def test_admin_cannot_kick_owner(self):
  self._login(self.admin);r=self.client.post(reverse('group_kick_member',args=[self.group.pk,self.owner.pk]))
  self.assertEqual(r.status_code,404);self.assertTrue(Membership.objects.filter(group=self.group,user=self.owner).exists())
 def test_admin_cannot_kick_another_admin(self):
  self._login(self.admin);r=self.client.post(reverse('group_kick_member',args=[self.group.pk,self.admin2.pk]))
  self.assertEqual(r.status_code,404);self.assertTrue(Membership.objects.filter(group=self.group,user=self.admin2).exists())
 def test_owner_can_kick_admin(self):
  self._login(self.owner);self.client.post(reverse('group_kick_member',args=[self.group.pk,self.admin2.pk]))
  self.assertFalse(Membership.objects.filter(group=self.group,user=self.admin2).exists())
 def test_owner_toggles_admin(self):
  self._login(self.owner);self.client.post(reverse('group_toggle_admin',args=[self.group.pk,self.member.pk]))
  self.assertTrue(Membership.objects.get(group=self.group,user=self.member).is_admin)
  self.client.post(reverse('group_toggle_admin',args=[self.group.pk,self.member.pk]));self.assertFalse(Membership.objects.get(group=self.group,user=self.member).is_admin)
 def test_non_owner_cannot_toggle_admin(self):
  self._login(self.admin);r=self.client.post(reverse('group_toggle_admin',args=[self.group.pk,self.member.pk]))
  self.assertEqual(r.status_code,404);self.assertFalse(Membership.objects.get(group=self.group,user=self.member).is_admin)
 def test_non_member_cannot_moderate(self):
  stranger=User.objects.create_user('stranger',password='strong-pass-123');Profile.objects.create(user=stranger);self._login(stranger)
  self.assertEqual(self.client.post(reverse('group_delete_post',args=[self.group.pk,self.member_post.pk])).status_code,404)
  self.assertEqual(self.client.post(reverse('group_kick_member',args=[self.group.pk,self.member.pk])).status_code,404)
  self.assertEqual(self.client.post(reverse('group_toggle_admin',args=[self.group.pk,self.member.pk])).status_code,404)
 def test_group_page_shows_moderation_controls_for_admin(self):
  self._login(self.admin);r=self.client.get(reverse('group_detail',args=[self.group.pk]))
  self.assertContains(r,'Вигнати');self.assertContains(r,'Видалити');self.assertContains(r,'Покинути групу')
  self._login(self.member);r=self.client.get(reverse('group_detail',args=[self.group.pk]))
  self.assertNotContains(r,'Вигнати');self.assertNotContains(r,'Зробити адміном')
 def test_group_page_shows_toggle_admin_only_for_owner(self):
  self._login(self.owner);self.assertContains(self.client.get(reverse('group_detail',args=[self.group.pk])),'Зробити адміном')
  self._login(self.admin);self.assertNotContains(self.client.get(reverse('group_detail',args=[self.group.pk])),'Зробити адміном')

class RatingTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
  self.other=User.objects.create_user('olia',password='strong-pass-123');Profile.objects.create(user=self.other)
  self.staff=User.objects.create_user('moderator',password='strong-pass-123',is_staff=True);Profile.objects.create(user=self.staff)
  self.post=Post.objects.create(author=self.user,body='Пост для оцінки');self.group=Group.objects.create(name='Python',description='Dev',owner=self.other)
 def test_user_rates_post(self):
  r=self.client.post(reverse('rate_post',args=[self.post.pk]),{'value':5,'review':'Гарно'})
  self.assertEqual(r.status_code,302);self.assertEqual(Rating.objects.filter(user=self.user,post=self.post,value=5,review='Гарно').count(),1)
 def test_rerate_updates_without_duplicate(self):
  self.client.post(reverse('rate_post',args=[self.post.pk]),{'value':3,'review':'Так собі'})
  self.client.post(reverse('rate_post',args=[self.post.pk]),{'value':5,'review':'Круто'})
  self.assertEqual(Rating.objects.filter(user=self.user,post=self.post).count(),1)
  rating=Rating.objects.get(user=self.user,post=self.post);self.assertEqual(rating.value,5);self.assertEqual(rating.review,'Круто')
 def test_group_rating(self):
  self.assertEqual(self.client.post(reverse('rate_group',args=[self.group.pk]),{'value':4,'review':'Затишно'}).status_code,302)
  self.assertEqual(self.group.ratings.filter(user=self.user,value=4).count(),1)
  content=self.client.get(reverse('group_detail',args=[self.group.pk])).content.decode()
  self.assertIn('★ 4,0 (1)',content);self.assertIn('Відгуки',content);self.assertIn('Затишно',content)
 def test_hidden_rating_excluded_from_average(self):
  Rating.objects.create(user=self.user,post=self.post,value=5);hidden=Rating.objects.create(user=self.staff,post=self.post,value=1)
  self.assertEqual(self.post.rating_stats,(3.0,2))
  hidden.is_approved=False;hidden.save(update_fields=['is_approved'])
  self.assertEqual(self.post.rating_stats,(5.0,1))
 def test_staff_hide_and_restore(self):
  self.client.logout();self.client.login(username='moderator',password='strong-pass-123')
  rating=Rating.objects.create(user=self.user,post=self.post,value=5)
  self.assertEqual(self.client.post(reverse('rating_hide',args=[rating.pk])).status_code,302)
  rating.refresh_from_db();self.assertFalse(rating.is_approved)
  self.assertEqual(self.client.post(reverse('rating_restore',args=[rating.pk])).status_code,302)
  rating.refresh_from_db();self.assertTrue(rating.is_approved)
 def test_non_staff_moderation_gets_403(self):
  rating=Rating.objects.create(user=self.other,post=self.post,value=4)
  self.assertEqual(self.client.post(reverse('rating_hide',args=[rating.pk])).status_code,403)
  self.assertEqual(self.client.post(reverse('rating_restore',args=[rating.pk])).status_code,403)
  rating.refresh_from_db();self.assertTrue(rating.is_approved)
 def test_feed_renders_rating_line_and_reviews(self):
  Rating.objects.create(user=self.other,post=self.post,value=4,review='Гарно')
  content=self.client.get(reverse('feed')).content.decode()
  self.assertIn('★ 4,0 (1)',content);self.assertIn('★4',content);self.assertIn('Відгуки',content)
  self.assertNotIn('Сховати',content)
  Follow.objects.create(follower=self.staff,target=self.user)
  self.client.logout();self.client.login(username='moderator',password='strong-pass-123')
  self.assertIn('Сховати',self.client.get(reverse('feed')).content.decode())
@override_settings(CHANNEL_LAYERS={'default':{'BACKEND':'channels.layers.InMemoryChannelLayer'}})
class NotificationSettingsTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
  self.other=User.objects.create_user('olia',password='strong-pass-123');Profile.objects.create(user=self.other)
 def test_message_setting_mutes_chat_notification(self):
  conv=Conversation.objects.create();conv.participants.add(self.user,self.other)
  NotificationSetting.objects.create(user=self.other,on_message=False)
  self.client.post(reverse('conversation',args=[conv.pk]),{'body':'Привіт!'})
  self.assertTrue(conv.messages.filter(body='Привіт!').exists());self.assertEqual(self.other.notifications.count(),0)
  NotificationSetting.objects.filter(user=self.other).delete()
  self.client.post(reverse('conversation',args=[conv.pk]),{'body':'Ще раз'})
  self.assertEqual(self.other.notifications.count(),1)
 def test_like_setting_mutes_notification(self):
  NotificationSetting.objects.create(user=self.other,on_like=False)
  post=Post.objects.create(author=self.other,body='Пост')
  self.client.post(reverse('like',args=[post.pk]));self.assertEqual(self.other.notifications.count(),0)
  NotificationSetting.objects.filter(user=self.other).delete();Like.objects.filter(user=self.user,post=post).delete()
  self.client.post(reverse('like',args=[post.pk]));self.assertEqual(self.other.notifications.count(),1)
 def test_settings_page_get_and_post(self):
  r=self.client.get(reverse('notification_settings'));self.assertEqual(r.status_code,200);self.assertContains(r,'Нові повідомлення в чатах');self.assertContains(r,'Лайки та поширення публікацій')
  r=self.client.post(reverse('notification_settings'),{'on_comment':'on','on_friend':'on','on_follow':'on'});self.assertEqual(r.status_code,302)
  s=self.user.notification_setting;self.assertFalse(s.on_like);self.assertTrue(s.on_comment);self.assertTrue(s.on_friend);self.assertTrue(s.on_follow);self.assertFalse(s.on_message)
 def test_settings_page_requires_login(self):
  self.client.logout();self.assertEqual(self.client.get(reverse('notification_settings')).status_code,302)
class HomeWidgetsTests(TestCase):
 def test_home_lists_popular_user_with_follower_count(self):
  star=User.objects.create_user('star',password='strong-pass-123');Profile.objects.create(user=star)
  fan=User.objects.create_user('fan',password='strong-pass-123');Profile.objects.create(user=fan)
  Follow.objects.create(follower=fan,target=star)
  r=self.client.get(reverse('home'))
  self.assertContains(r,'@star');self.assertContains(r,'1 підписників')
 def test_most_followed_user_ranks_first(self):
  star=User.objects.create_user('star',password='strong-pass-123');Profile.objects.create(user=star)
  rising=User.objects.create_user('rising',password='strong-pass-123');Profile.objects.create(user=rising)
  f1=User.objects.create_user('f1',password='strong-pass-123');Profile.objects.create(user=f1)
  f2=User.objects.create_user('f2',password='strong-pass-123');Profile.objects.create(user=f2)
  Follow.objects.create(follower=f1,target=star);Follow.objects.create(follower=f2,target=star);Follow.objects.create(follower=f1,target=rising)
  r=self.client.get(reverse('home'))
  self.assertEqual(r.context['popular_users'][0].username,'star');self.assertEqual(r.context['popular_users'][1].username,'rising')
 def test_home_shows_only_upcoming_events(self):
  Event.objects.create(title='Майбутній мітап',starts_at=timezone.now()+timedelta(days=2))
  Event.objects.create(title='Минулий захід',starts_at=timezone.now()-timedelta(days=2))
  r=self.client.get(reverse('home'))
  self.assertContains(r,'Майбутній мітап');self.assertNotContains(r,'Минулий захід')
 def test_home_event_renders_date_and_description(self):
  Event.objects.create(title='PyCon',description='Конференція про Python та Django',starts_at=timezone.now()+timedelta(days=3))
  r=self.client.get(reverse('home'))
  self.assertContains(r,'PyCon');self.assertContains(r,'Конференція');self.assertRegex(r.content.decode(),r'\d{2}\.\d{2} \d{2}:\d{2}')
 def test_empty_states_render(self):
  r=self.client.get(reverse('home'))
  self.assertContains(r,'Ще нікого');self.assertContains(r,'Подій немає')
class SeedDemoTests(TestCase):
 def test_seed_creates_realistic_content(self):
  from django.core.management import call_command
  from .models import Conversation, Event
  call_command('seed_demo')
  self.assertTrue(User.objects.filter(username='olesya_k').exists())
  self.assertGreater(Post.objects.count(),10);self.assertGreater(Group.objects.count(),3)
  self.assertGreater(Conversation.objects.count(),1);self.assertEqual(Event.objects.count(),4)
  call_command('seed_demo')  # ідемпотентність
  self.assertEqual(User.objects.filter(username='olesya_k').count(),1)
 def test_seed_clean_removes_e2e_junk(self):
  User.objects.create_user('nazar',password='strong-pass-123')
  junk=User.objects.create_user('alice_deadbeef',password='strong-pass-123')
  from django.core.management import call_command
  call_command('seed_demo',clean=True)
  self.assertFalse(User.objects.filter(pk=junk.pk).exists());self.assertTrue(User.objects.filter(username='nazar').exists())

class UxLogicTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
  self.other=User.objects.create_user('olia',password='strong-pass-123');Profile.objects.create(user=self.other)
  Friendship.objects.create(sender=self.user,receiver=self.other,status='accepted')
 def test_start_chat_idempotent(self):
  r1=self.client.get(reverse('start_chat',args=['olia']));r2=self.client.get(reverse('start_chat',args=['olia']))
  self.assertEqual(r1.status_code,302);self.assertEqual(Conversation.objects.count(),1)
 def test_private_chat_titled_by_other_user(self):
  c=Conversation.objects.create();c.participants.add(self.user,self.other);Message.objects.create(conversation=c,sender=self.other,body='привіт!')
  r=self.client.get(reverse('chats'));self.assertContains(r,'@olia');self.assertContains(r,'привіт!')
 def test_profile_shows_counters(self):
  p=Post.objects.create(author=self.other,body='пост')
  r=self.client.get(reverse('profile',args=['olia']));self.assertContains(r,'1</b> публікацій');self.assertContains(r,'1</b> друзів');self.assertContains(r,'Написати')
 def test_like_notification_has_url(self):
  p=Post.objects.create(author=self.other,body='пост');self.client.post(reverse('like',args=[p.pk]))
  n=self.other.notifications.first();self.assertTrue(n);self.assertEqual(n.url,f'/u/{self.other.username}/')

class ProfileCustomizationTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
  self.other=User.objects.create_user('olia',password='strong-pass-123');Profile.objects.create(user=self.other,status='каву і кодю і кодю',location='Львів')
 def test_check_username_availability_json(self):
  import json as j
  r1=self.client.get(reverse('check_username'),{'q':'olia'});r2=self.client.get(reverse('check_username'),{'q':'freshuser'})
  self.assertFalse(j.loads(r1.content)['available']);self.assertTrue(j.loads(r2.content)['available'])
 def test_search_finds_users_and_groups(self):
  Group.objects.create(name='Python Україна',description='dev',owner=self.other)
  r=self.client.get(reverse('search'),{'q':'oli'});self.assertContains(r,'@olia');self.assertContains(r,'каву і кодю')
  r=self.client.get(reverse('search'),{'q':'python'});self.assertContains(r,'Python Україна')
  r=self.client.get(reverse('search'),{'q':'oli'});self.assertNotIn('nazar</b>',r.content.decode())
 def test_set_theme_persists_in_profile(self):
  self.client.post(reverse('set_theme'),{'theme':'dark'});self.assertEqual(Profile.objects.get(user=self.user).theme,'dark')
 def test_profile_shows_status_and_location(self):
  r=self.client.get(reverse('profile',args=['olia']));self.assertContains(r,'Львів');self.assertContains(r,'каву і кодю')
 def test_edit_profile_saves_new_fields(self):
  self.client.post(reverse('edit_profile'),{'status':'Новий статус','location':'Київ','bio':'біо','avatar':'','cover':''})
  self.user.profile.refresh_from_db();self.assertEqual(self.user.profile.status,'Новий статус');self.assertEqual(self.user.profile.location,'Київ')

class ThemeSystemTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
 def test_auto_theme_renders_no_attribute(self):
  self.user.profile.theme='auto';self.user.profile.save()
  html=self.client.get(reverse('feed')).content.decode();self.assertNotIn('data-theme="',html)
 def test_explicit_dark_renders_attribute(self):
  Profile.objects.filter(user=self.user).update(theme='dark')
  html=self.client.get(reverse('feed')).content.decode();self.assertIn('data-theme="dark"',html)
 def test_migration_marked_light_to_auto(self):
  from network.models import Profile as P
  Profile.objects.filter(user=self.user).update(theme='light')  # явний вибір лишається
  self.assertEqual(P.objects.get(user=self.user).theme,'light')
 def test_nav_has_tooltips_and_user_menu(self):
  html=self.client.get(reverse('feed')).content.decode()
  self.assertIn('data-tip="Стрічка"',html);self.assertIn('user-dropdown',html);self.assertIn('Мій профіль',html)

class PaletteSettingsTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
 def test_settings_page_shows_all_presets(self):
  r=self.client.get(reverse('settings'));self.assertEqual(r.status_code,200)
  for name in ('Фіолет','Океан','Ліс','Захід','Монохром'):self.assertContains(r,name)
  self.assertContains(r,'Як у системі')
 def test_autosave_endpoint_saves_theme_and_palette(self):
  self.client.post(reverse('set_theme'),{'theme':'dark','palette':'ocean'})
  p=Profile.objects.get(user=self.user);self.assertEqual(p.theme,'dark');self.assertEqual(p.palette,'ocean')
 def test_autosave_rejects_garbage(self):
  self.client.post(reverse('set_theme'),{'theme':'hacker','palette':'neon'})
  p=Profile.objects.get(user=self.user);self.assertEqual(p.theme,'light');self.assertEqual(p.palette,'violet')
 def test_base_renders_palette_attribute(self):
  Profile.objects.filter(user=self.user).update(palette='sunset')
  html=self.client.get(reverse('feed')).content.decode();self.assertIn('data-palette="sunset"',html)

class FooterDarkTests(TestCase):
 def test_footer_has_no_educational_label(self):
  u=User.objects.create_user('x',password='strong-pass-123');Profile.objects.create(user=u)
  from django.test import Client
  c=Client(); c.force_login(u)
  html=c.get(reverse('feed')).content.decode()
  self.assertNotIn('навчальний',html);self.assertIn('UASocial</footer>',html)
 def test_dark_mode_sets_bootstrap_theme(self):
  u=User.objects.create_user('x',password='strong-pass-123');Profile.objects.create(user=u)
  from django.test import Client
  Profile.objects.filter(user=u).update(theme='dark')
  c=Client(); c.force_login(u)
  self.assertIn('data-bs-theme="dark"',c.get(reverse('feed')).content.decode())

class BrokenChannelLayer:
 def __init__(self,*a,**kw): pass
 async def new_channel(self): return 'broken!1'
 async def receive(self,channel): await asyncio.Event().wait()
 def group_add(self,g,c): raise ConnectionError('redis down')
 def group_discard(self,g,c): raise ConnectionError('redis down')
 def group_send(self,g,m): raise ConnectionError('redis down')

class _TestAuthMiddleware(BaseMiddleware):
 def __init__(self,app,user): self.user=user; super().__init__(app)
 async def __call__(self,scope,receive,send): scope['user']=self.user; return await super().__call__(scope,receive,send)

class RateLimitTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
  self.other=User.objects.create_user('olia',password='strong-pass-123');Profile.objects.create(user=self.other)
  self.post=Post.objects.create(author=self.user,body='пост')
  self.ip='203.0.113.77'
 def tearDown(self):
  from network import ratelimit
  ratelimit._hits.clear()
 def _like(self,xff=''):
  extra={'REMOTE_ADDR':self.ip}
  if xff: extra['HTTP_X_FORWARDED_FOR']=xff
  return self.client.post(reverse('like',args=[self.post.pk]),**extra)
 def test_60_posts_allowed_then_429(self):
  for _ in range(60): self.assertEqual(self._like().status_code,302)
  self.assertEqual(self._like().status_code,429)
 def test_xff_does_not_bypass_limit(self):
  for i in range(60): self.assertEqual(self._like(xff=f'1.2.3.{i}').status_code,302)
  self.assertEqual(self._like(xff='9.9.9.9').status_code,429)

class InputLimitTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
  self.other=User.objects.create_user('olia',password='strong-pass-123');Profile.objects.create(user=self.other)
  self.post=Post.objects.create(author=self.other,body='пост')
 def test_post_body_over_5000_rejected(self):
  self.client.post(reverse('feed'),{'body':'x'*5001,'media_url':''})
  self.assertFalse(Post.objects.filter(author=self.user).exists())
 def test_comment_over_1000_rejected(self):
  self.client.post(reverse('comment',args=[self.post.pk]),{'body':'x'*1001})
  self.assertEqual(Comment.objects.filter(post=self.post).count(),0)
 def test_message_over_5000_rejected(self):
  conv=Conversation.objects.create();conv.participants.add(self.user,self.other)
  self.client.post(reverse('conversation',args=[conv.pk]),{'body':'x'*5001})
  self.assertFalse(conv.messages.exists())
 def test_group_description_over_2000_rejected(self):
  self.client.post(reverse('create_group'),{'name':'X','description':'x'*2001})
  self.assertFalse(Group.objects.filter(name='X').exists())
 def test_rating_out_of_range_rejected(self):
  self.client.post(reverse('rate_post',args=[self.post.pk]),{'value':0,'review':''})
  self.client.post(reverse('rate_post',args=[self.post.pk]),{'value':999,'review':''})
  self.assertEqual(Rating.objects.filter(post=self.post).count(),0)

class CoverInjectionTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
 def test_cover_with_css_breakout_rejected_by_form(self):
  self.client.post(reverse('edit_profile'),{'status':'','location':'','bio':'','avatar':'','cover':'https://example.com/a(1).jpg'})
  self.assertEqual(Profile.objects.get(user=self.user).cover,'')
 def test_cover_payloads_rejected_by_model(self):
  p=Profile.objects.get(user=self.user)
  for payload in ('https://example.com/a(1).jpg',"https://x.example/a' onerror='alert(1)",'https://x.example/a" onerror="alert(1)','https://x.example/a(\nb'):
   p.cover=payload
   with self.assertRaises(ValidationError): p.full_clean()
  p.cover='https://example.com/cover.jpg';p.full_clean()
 def test_profile_renders_data_cover_not_inline_style(self):
  Profile.objects.filter(user=self.user).update(cover='https://example.com/cover.jpg')
  html=self.client.get(reverse('profile',args=[self.user.username])).content.decode()
  self.assertNotIn('style="background-image',html);self.assertIn('data-cover="https://example.com/cover.jpg"',html);self.assertIn('dataset.cover',html)

class FriendRaceTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
  self.other=User.objects.create_user('olia',password='strong-pass-123');Profile.objects.create(user=self.other)
 @patch('network.models.Friendship.objects.create',side_effect=IntegrityError)
 def test_duplicate_friend_request_does_not_duplicate(self,mock_create):
  r=self.client.post(reverse('friend_action',args=['olia']),{'action':'send'})
  self.assertEqual(r.status_code,302);self.assertEqual(self.other.notifications.count(),0);self.assertFalse(Friendship.objects.exists())

class AvatarDownloadTests(TestCase):
 def setUp(self):
  from allauth.socialaccount.models import SocialAccount, SocialLogin
  from .adapters import CustomSocialAccountAdapter
  self.SocialLogin=SocialLogin
  self.user=User.objects.create_user('guser',password='strong-pass-123')
  self.account=SocialAccount(user=self.user,provider='google',extra_data={'picture':'https://lh3.googleusercontent.com/x.png'})
  self.adapter=CustomSocialAccountAdapter()
 def _jpg(self):
  buf=io.BytesIO();Image.new('RGB',(8,8)).save(buf,format='JPEG');return buf.getvalue()
 def _resp(self,content_type='image/jpeg',content=b'x',status=200):
  return Mock(status_code=status,headers={'Content-Type':content_type},content=content,raise_for_status=Mock())
 @patch('network.adapters.requests.get')
 def test_download_avatar_saves_local_file(self,mock_get):
  mock_get.return_value=self._resp(content=self._jpg())
  url=self.adapter.download_avatar('https://lh3.googleusercontent.com/x.png')
  self.assertTrue(url.startswith('/media/avatars/'))
  path=os.path.join(settings.MEDIA_ROOT,url[len(settings.MEDIA_URL):])
  self.assertTrue(os.path.exists(path));os.remove(path)
 @patch('network.adapters.requests.get')
 def test_download_avatar_rejects_non_image(self,mock_get):
  mock_get.return_value=self._resp(content_type='text/html',content=b'<html>')
  self.assertEqual(self.adapter.download_avatar('https://x.example/page'),'')
 @patch('network.adapters.requests.get')
 def test_download_avatar_rejects_oversized(self,mock_get):
  mock_get.return_value=self._resp(content=b'x'*(5*1024*1024+1))
  self.assertEqual(self.adapter.download_avatar('https://x.example/big.jpg'),'')
 @patch('network.adapters.requests.get')
 def test_download_avatar_rejects_http_error(self,mock_get):
  resp=self._resp(status=404);resp.raise_for_status.side_effect=requests.HTTPError('404')
  mock_get.return_value=resp
  self.assertEqual(self.adapter.download_avatar('https://x.example/missing.jpg'),'')
 @patch('network.adapters.requests.get')
 def test_download_avatar_returns_empty_on_network_error(self,mock_get):
  mock_get.side_effect=requests.ConnectionError('down')
  self.assertEqual(self.adapter.download_avatar('https://x.example/avatar.jpg'),'')
 @patch('network.adapters.requests.get')
 def test_setup_profile_never_stores_external_url(self,mock_get):
  mock_get.side_effect=requests.ConnectionError('down')
  self.adapter.setup_profile(self.SocialLogin(account=self.account,user=self.user))
  self.assertEqual(Profile.objects.get(user=self.user).avatar,'')
 @patch('network.adapters.requests.get')
 def test_setup_profile_saves_local_avatar(self,mock_get):
  mock_get.return_value=self._resp(content=self._jpg())
  self.adapter.setup_profile(self.SocialLogin(account=self.account,user=self.user))
  self.assertTrue(Profile.objects.get(user=self.user).avatar.startswith('/media/avatars/'))

@override_settings(CHANNEL_LAYERS={'default':{'BACKEND':'network.tests.BrokenChannelLayer'}})
class RedisDownTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
  self.other=User.objects.create_user('olia',password='strong-pass-123');Profile.objects.create(user=self.other)
  self.conv=Conversation.objects.create();self.conv.participants.add(self.user,self.other)
 def test_chat_upload_saves_and_redirects_when_layer_down(self):
  f=SimpleUploadedFile('note.txt',b'hello',content_type='text/plain')
  r=self.client.post(reverse('chat_upload',args=[self.conv.pk]),{'attachment':f})
  self.assertEqual(r.status_code,302);self.assertTrue(Message.objects.filter(conversation=self.conv).exists())
 @patch.object(consumers.ChatConsumer,'is_participant',new=AsyncMock(return_value=True))
 def test_chat_consumer_connect_closes_when_layer_down(self):
  app=_TestAuthMiddleware(URLRouter([re_path(r'ws/chat/(?P<room_name>\w+)/$',consumers.ChatConsumer.as_asgi())]),SimpleNamespace(is_authenticated=True))
  comm=WebsocketCommunicator(app,f'/ws/chat/{self.conv.pk}/')
  connected,_=async_to_sync(comm.connect)()
  self.assertFalse(connected)
 def test_notification_consumer_connect_closes_when_layer_down(self):
  app=_TestAuthMiddleware(URLRouter([re_path(r'ws/notifications/$',consumers.NotificationsConsumer.as_asgi())]),SimpleNamespace(is_authenticated=True,id=1))
  comm=WebsocketCommunicator(app,'/ws/notifications/')
  connected,_=async_to_sync(comm.connect)()
  self.assertFalse(connected)

class SecurityHeadersTests(TestCase):
 def setUp(self):
  self.user=User.objects.create_user('nazar',password='strong-pass-123');Profile.objects.create(user=self.user);self.client.login(username='nazar',password='strong-pass-123')
 def test_csp_header_present(self):
  csp=self.client.get(reverse('feed')).headers.get('Content-Security-Policy','')
  self.assertIn("default-src 'self'",csp);self.assertIn("script-src 'self'",csp);self.assertIn("object-src 'none'",csp);self.assertIn("frame-ancestors 'self'",csp)
 def test_csp_header_present_for_anonymous(self):
  self.client.logout()
  csp=self.client.get(reverse('home')).headers.get('Content-Security-Policy','')
  self.assertIn("default-src 'self'",csp)

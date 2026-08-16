from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import Conversation, Friendship, Group, Like, Membership, NotificationSetting, Post, Profile
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

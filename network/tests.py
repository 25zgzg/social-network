from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import Conversation, Event, Follow, Friendship, Group, Like, Membership, Message, NotificationSetting, Post, Profile, Rating
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
 def test_non_staff_moderation_gets_404(self):
  rating=Rating.objects.create(user=self.other,post=self.post,value=4)
  self.assertEqual(self.client.post(reverse('rating_hide',args=[rating.pk])).status_code,404)
  self.assertEqual(self.client.post(reverse('rating_restore',args=[rating.pk])).status_code,404)
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

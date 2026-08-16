from django.urls import path
from . import views
urlpatterns=[
 path('',views.home,name='home'),path('signup/',views.signup,name='signup'),path('feed/',views.feed,name='feed'),
 path('u/<str:username>/',views.profile,name='profile'),path('profile/edit/',views.edit_profile,name='edit_profile'),
 path('posts/<int:pk>/like/',views.toggle_like,name='like'),path('posts/<int:pk>/comment/',views.add_comment,name='comment'),path('posts/<int:pk>/share/',views.share_post,name='share'),
 path('u/<str:username>/follow/',views.follow,name='follow'),path('u/<str:username>/friend/',views.friend_action,name='friend_action'),path('friends/',views.friend_requests,name='friends'),
 path('groups/new/',views.create_group,name='create_group'),path('groups/',views.groups_list,name='groups'),path('groups/<int:pk>/',views.group_detail,name='group_detail'),path('groups/<int:pk>/join/',views.join_group,name='join_group'),
 path('groups/<int:pk>/leave/',views.leave_group,name='leave_group'),path('groups/<int:pk>/posts/<int:post_pk>/delete/',views.group_delete_post,name='group_delete_post'),
 path('groups/<int:pk>/members/<int:user_id>/kick/',views.group_kick_member,name='group_kick_member'),path('groups/<int:pk>/members/<int:user_id>/toggle-admin/',views.group_toggle_admin,name='group_toggle_admin'),
 path('notifications/',views.notifications,name='notifications'),path('notifications/settings/',views.notification_settings,name='notification_settings'),
 path('chats/',views.chats,name='chats'),path('chats/new/',views.conversation_create,name='conversation_create'),path('chats/<int:pk>/',views.conversation,name='conversation'),path('chats/<int:pk>/upload/',views.chat_upload,name='chat_upload'),
]

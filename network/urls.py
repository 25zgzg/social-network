from django.urls import path
from . import views
urlpatterns=[
 path('',views.home,name='home'),path('signup/',views.signup,name='signup'),path('feed/',views.feed,name='feed'),
 path('u/<str:username>/',views.profile,name='profile'),path('profile/edit/',views.edit_profile,name='edit_profile'),
 path('posts/<int:pk>/like/',views.toggle_like,name='like'),path('posts/<int:pk>/comment/',views.add_comment,name='comment'),
 path('u/<str:username>/follow/',views.follow,name='follow'),path('u/<str:username>/friend/',views.friend_action,name='friend_action'),path('friends/',views.friend_requests,name='friends'),
 path('groups/new/',views.create_group,name='create_group'),path('groups/<int:pk>/',views.group_detail,name='group_detail'),path('groups/<int:pk>/join/',views.join_group,name='join_group'),
 path('notifications/',views.notifications,name='notifications'),path('chats/',views.chats,name='chats'),path('chats/<int:pk>/',views.conversation,name='conversation'),
]

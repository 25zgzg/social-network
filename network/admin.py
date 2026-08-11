from django.contrib import admin
from .models import *
admin.site.register([Profile,Friendship,Follow,Group,Membership,Post,Like,Comment,Notification,Conversation,Message,Rating])

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import Comment, Group, Message, NotificationSetting, Post, Profile, Rating

User=get_user_model()
class SignupForm(UserCreationForm):
    email=forms.EmailField(required=True)
    class Meta(UserCreationForm.Meta): model=User; fields=('username','email','first_name','last_name')
class ProfileForm(forms.ModelForm):
    class Meta: model=Profile; fields=('bio','avatar','cover')
class PostForm(forms.ModelForm):
    class Meta: model=Post; fields=('body','media_url'); widgets={'body':forms.Textarea(attrs={'rows':3,'placeholder':'Що нового?'})}
class CommentForm(forms.ModelForm):
    class Meta: model=Comment; fields=('body',); widgets={'body':forms.TextInput(attrs={'placeholder':'Коментар...'})}
class GroupForm(forms.ModelForm):
    class Meta: model=Group; fields=('name','description')
class MessageForm(forms.ModelForm):
    class Meta: model=Message; fields=('body',)
class ConversationForm(forms.Form):
    title=forms.CharField(max_length=120,required=False,label='Назва (для групового чату)')
    participants=forms.ModelMultipleChoiceField(queryset=User.objects.none(),label='Учасники',help_text='Оберіть друзів — можна кількох для групового чату')
class RatingForm(forms.ModelForm):
    class Meta: model=Rating; fields=('value','review'); widgets={'value':forms.NumberInput(attrs={'min':1,'max':5})}
class NotificationSettingForm(forms.ModelForm):
    class Meta:
        model=NotificationSetting; fields=('on_like','on_comment','on_friend','on_follow','on_message')
        labels={'on_like':'Лайки та поширення публікацій','on_comment':'Коментарі','on_friend':'Запити в друзі','on_follow':'Нові підписники','on_message':'Нові повідомлення в чатах'}

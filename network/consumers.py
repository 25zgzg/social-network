import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_text = data.get('message', '')
        if not message_text:
            return
        # save message to DB and prepare payload
        msg = await self.create_message(message_text)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message',
                'message': msg,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({'message': event['message']}))

    @database_sync_to_async
    def create_message(self, message_text):
        conv = Conversation.objects.get(pk=int(self.room_name))
        # scope.user is available on the consumer instance
        sender = self.scope.get('user')
        if sender is None or not sender.is_authenticated:
            # anonymous fallback (shouldn't happen with login_required on view)
            sender = User.objects.filter(is_active=True).first()
        msg = Message.objects.create(conversation=conv, sender=sender, body=message_text)
        return {
            'id': msg.pk,
            'sender': msg.sender.username,
            'body': msg.body,
            'created_at': msg.created_at.strftime('%H:%M'),
        }

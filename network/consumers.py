import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation, message_payload, notify_message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        user = self.scope.get('user')
        if user is None or not user.is_authenticated or not await self.is_participant():
            await self.close()
            return
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    @database_sync_to_async
    def is_participant(self):
        try:
            Conversation.objects.get(pk=int(self.room_name), participants=self.scope['user'])
        except (Conversation.DoesNotExist, ValueError, TypeError):
            return False
        return True

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_text = data.get('message', '')
        if not message_text:
            return
        msg = await self.create_message(message_text)
        if msg is None:
            await self.close()
            return
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
        sender = self.scope.get('user')
        if sender is None or not sender.is_authenticated:
            return None
        msg = conv.messages.create(sender=sender, body=message_text)
        notify_message(msg)
        return message_payload(msg)

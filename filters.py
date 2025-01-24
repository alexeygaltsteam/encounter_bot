from aiogram.types import Message
from aiogram.filters import BaseFilter


class PrivateChatFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.chat.type == "private"

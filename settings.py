from typing import List

from pydantic import field_validator
from pydantic.v1 import BaseSettings, validator
import os

# DB_HOST = os.getenv("DB_HOST")
# DB_PORT = os.getenv("DB_PORT")
# DB_USER = os.getenv("DB_USER")
# DB_PASS = os.getenv("DB_PASS")
# DB_NAME = os.getenv("DB_NAME")
# BOT_TOKEN = os.getenv("BOT_TOKEN")
# CHAT_ID = os.getenv("CHAT_ID")
# print(CHAT_ID)

ADMINS = []


class Settings(BaseSettings):
    # DB_HOST: str = DB_HOST
    # DB_PORT: int = DB_PORT
    # DB_USER: str = DB_USER
    # DB_PASS: str = DB_PASS
    # DB_NAME: str = DB_NAME
    # BOT_TOKEN: str = BOT_TOKEN
    # CHAT_ID: str = CHAT_ID.split()
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str
    BOT_TOKEN: str
    CHATS_ID: str

    @property
    def get_database_url(self):
        return f'postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    @property
    def get_chat_ids(self):
        if self.CHATS_ID:
            return [chat_id.strip() for chat_id in self.CHATS_ID.split(',')]
        return []
    class Config:
        env_file = '.env'


settings = Settings()
CHATS_ID = settings.get_chat_ids

DATABASE_URL = settings.get_database_url

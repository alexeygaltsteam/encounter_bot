from pydantic.v1 import BaseSettings
import os

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ADMINS = []


class Settings(BaseSettings):
    DB_HOST: str = DB_HOST
    DB_PORT: int = DB_PORT
    DB_USER: str = DB_USER
    DB_PASS: str = DB_PASS
    DB_NAME: str = DB_NAME
    BOT_TOKEN: str = BOT_TOKEN
    CHAT_ID: str = CHAT_ID

    @property
    def get_database_url(self):
        return f'postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    # class Config:
    #     env_file = '.env'


settings = Settings()

DATABASE_URL = settings.get_database_url

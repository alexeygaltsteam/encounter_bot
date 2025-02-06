from aiogram import Bot, Dispatcher
from db.dao import *
from settings import DATABASE_URL, settings
from db import DatabaseManager

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

# storage = MemoryStorage()


db = DatabaseManager(DATABASE_URL)

# game_dao = GameDateDAO(db.async_session())
game_dao = GameDateDAO(db.async_session)
user_dao = UserDAO(db.async_session)
user_subs_dao = UserGameSubscriptionDAO(db.async_session)
user_role_dao = UserGameRoleDAO(db.async_session)

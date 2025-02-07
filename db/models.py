# from sqlalchemy.orm import declarative_base
# from sqlalchemy import Column, Integer, String, DateTime, Boolean, text, Table, ForeignKey
# from enum import Enum
# from sqlalchemy.orm import relationship
#
# Base = declarative_base()
#
#
# class PlayerRole(Enum):
#     LOOKING_FOR_GAME = "looking_for_game"
#     LOOKING_FOR_TEAM = "looking_for_team"
#
#
# class UserGameSubscription(Base):
#     __tablename__ = "user_game_subscription"
#
#     user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
#     game_id = Column(Integer, ForeignKey("game_dates.id", ondelete="CASCADE"), primary_key=True)
#
#     user = relationship("User", back_populates="subscribed_games")
#     game = relationship("GameDate", back_populates="subscribers")
#
#     def __repr__(self):
#         return f"<UserGameSubscription(user_id={self.user_id}, game_id={self.game_id})>"
#
#
# class UserGameRole(Base):
#     __tablename__ = "user_game_role"
#
#     user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
#     game_id = Column(Integer, ForeignKey("game_dates.id", ondelete="CASCADE"), primary_key=True)
#     role = Column(String, nullable=False)
#
#     user = relationship("User", back_populates="game_roles")
#     game = relationship("GameDate", back_populates="players_with_roles")
#
#     def __repr__(self):
#         return f"<UserGameRole(user_id={self.user_id}, game_id={self.game_id}, role={self.role})>"
#
#
# class User(Base):
#     __tablename__ = "users"
#
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     telegram_id = Column(Integer, nullable=False, unique=True)
#     nickname = Column(String, nullable=False)
#
#     subscribed_games = relationship("GameDate", secondary="user_game_subscription", back_populates="subscribers")
#     game_roles = relationship("GameDate", secondary="user_game_role", back_populates="players_with_roles")
#
#     def __repr__(self):
#         return f"<User(id={self.id}, telegram_id={self.telegram_id}, nickname='{self.nickname}')>"
#
#
# class GameState(Enum):
#     UPCOMING = 0  # предстоящая
#     ACTIVE = 1  # активная
#     COMPLETED = 2  # завершенная
#
#
# class GameDate(Base):
#     __tablename__ = "game_dates"
#
#     id = Column(Integer, primary_key=True, autoincrement=False)
#     domain = Column(String, nullable=False)
#     start_date = Column(DateTime, nullable=False)
#     end_date = Column(DateTime, nullable=True)
#     name = Column(String, nullable=False)
#     author = Column(String, nullable=False)
#     price = Column(String, nullable=False)
#     link = Column(String, nullable=True)
#     game_type = Column(String, nullable=False)
#     max_players = Column(Integer, nullable=True)
#     state = Column(Integer, nullable=False, default=GameState.UPCOMING.value)
#     is_announcement_sent = Column(Boolean, nullable=False, default=False, server_default=text('false'))
#     is_start_message_sent = Column(Boolean, nullable=False, default=False, server_default=text('false'))
#
#     subscribers = relationship("User", secondary="user_game_subscription", back_populates="subscribed_games")
#     players_with_roles = relationship("User", secondary="user_game_role", back_populates="game_roles")
#
#     def __repr__(self):
#         return f"<GameDate(id={self.id}, name='{self.name}')>"

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Boolean, Enum, text, BigInteger
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum as PyEnum

Base = declarative_base()


class PlayerRole(PyEnum):
    LOOKING_FOR_GAME = "looking_for_game"
    LOOKING_FOR_TEAM = "looking_for_team"


class GameState(PyEnum):
    UPCOMING = 0  # предстоящая
    ACTIVE = 1  # активная
    COMPLETED = 2  # завершенная


class UserGameSubscription(Base):
    __tablename__ = "user_game_subscription"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    game_id = Column(Integer, ForeignKey("game_dates.id", ondelete="CASCADE"), primary_key=True)

    # Связь с пользователем
    user = relationship("User", backref=backref("subscribed_games", cascade="all, delete-orphan"))
    # Связь с игрой
    game = relationship("GameDate", backref=backref("subscribers", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<UserGameSubscription(user_id={self.user_id}, game_id={self.game_id})>"


class UserGameRole(Base):
    __tablename__ = "user_game_role"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    game_id = Column(Integer, ForeignKey("game_dates.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String, nullable=False)

    # Связь с пользователем
    user = relationship("User", backref=backref("game_roles", cascade="all, delete-orphan"))
    # Связь с игрой
    game = relationship("GameDate", backref=backref("players_with_roles", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<UserGameRole(user_id={self.user_id}, game_id={self.game_id}, role={self.role})>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, nullable=False, unique=True)
    nickname = Column(String, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, nickname='{self.nickname}')>"


class GameDate(Base):
    __tablename__ = "game_dates"

    id = Column(Integer, primary_key=True, autoincrement=False)
    domain = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    name = Column(String, nullable=False)
    author = Column(String, nullable=False)
    price = Column(String, nullable=False)
    link = Column(String, nullable=True)
    game_type = Column(String, nullable=False)
    max_players = Column(Integer, nullable=True)
    state = Column(Integer, nullable=False, default=GameState.UPCOMING.value)
    is_announcement_sent = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    is_start_message_sent = Column(Boolean, nullable=False, default=False, server_default=text('false'))

    def __repr__(self):
        return f"<GameDate(id={self.id}, name='{self.name}')>"

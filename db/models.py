from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, text
from enum import Enum

Base = declarative_base()


class GameState(Enum):
    UPCOMING = 0 # предстоящая
    ACTIVE = 1  # активная
    COMPLETED = 2  # завершенная


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
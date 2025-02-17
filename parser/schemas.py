from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from datetime import datetime

EMPTY_FIELD = "Нет информации"

MONTHS_MAP = {
    "января": "January",
    "февраля": "February",
    "марта": "March",
    "апреля": "April",
    "мая": "May",
    "июня": "June",
    "июля": "July",
    "августа": "August",
    "сентября": "September",
    "октября": "October",
    "ноября": "November",
    "декабря": "December",
}


def translate_date(date_str: str) -> str:
    """Переводит русские месяцы в английские для парсинга."""
    for ru_month, en_month in MONTHS_MAP.items():
        date_str = date_str.replace(ru_month, en_month)
    return date_str


class GameDate(BaseModel):
    id: int
    domain: str
    start_date: datetime
    end_date: Optional[datetime] = None
    name: str
    author: str
    price: str
    link: Optional[str] = None
    game_type: str
    max_players: Optional[int] = None
    image: Optional[str] = None

    @field_validator("start_date", mode="before")
    def parse_start_date(cls, value):
        """Валидатор для start_date."""
        if isinstance(value, str):
            try:
                translated_date = translate_date(value)
                return datetime.strptime(translated_date, "%d %B %Y г. %H:%M:%S")
                # return datetime.strptime(value, "%A, %B %d, %Y %I:%M:%S %p")
            except ValueError:
                # print(f"Invalid start_date format: {value}")
                # # Возвращаем недостижимую дату
                # unreachable_date = datetime(9999, 12, 31, 23, 59, 59)
                # return unreachable_date
                raise ValueError(f"Invalid start_date format: {value}")
        return value

    def update_end_date(self, value: str):
        """Метод для установки end_date с преобразованием."""
        if value is None:
            self.end_date = None
        else:
            try:
                self.end_date = datetime.strptime(value, "%d.%m.%Y %H:%M:%S")
            except ValueError:
                return None

    @field_validator('game_type')
    def validate_game_type(cls, value):
        if value not in ['team', 'single']:
            raise ValueError(f"Invalid game_type: {value}")
        return value

    @model_validator(mode="before")
    def generate_link(cls, values):
        domain = values.get('domain')
        game_id = values.get('id')
        if domain and game_id:
            values['link'] = f"https://{domain}/GameDetails.aspx?gid={game_id}&lang=ru"
        return values


class AdditionalData(BaseModel):
    end_date: str = EMPTY_FIELD
    max_players: str = EMPTY_FIELD
    image: Optional[str] = None

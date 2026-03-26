# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram-бот для отслеживания и анонсирования игр платформы Encounter (.en.cx / .encounter.cx). Парсит расписание игр, отправляет анонсы в каналы/группы, позволяет подписываться на игры и искать сокомандников.

## Development Commands

```bash
# Локальный запуск
python main.py

# Docker (поднимает PostgreSQL 15 + бот, миграции применяются автоматически)
docker-compose up --build

# Миграции
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

Тестов нет. Отладка — через `logs/logs.log` (ротация, три логгера: `bot_logger`, `parser_logger`, `db_logger`).

## Environment

Файл `.env` (загружается через `pydantic.v1.BaseSettings`):

- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_NAME` — PostgreSQL
- `BOT_TOKEN` — токен Telegram-бота
- `CHATS_ID` — ID чатов для анонсов (через запятую)

Python 3.11, ключевые зависимости: aiogram 3.17, SQLAlchemy 2.0 (asyncpg), APScheduler, BeautifulSoup4, pydantic 2.x (но Settings на pydantic.v1).

## Architecture

### Entry Point и Scheduling (`main.py`)

Инициализирует бот/диспетчер/БД из `loader.py`, регистрирует роутеры, запускает 4 cron-задачи (Moscow TZ):

| Задача | Расписание | Что делает |
|--------|-----------|------------|
| `run_parsing()` | :15, :45 | Парсит предстоящие игры, создаёт/обновляет в БД |
| `parsing_active_games()` | :55 | Парсит активные игры, обновляет статусы (ACTIVE→COMPLETED, UPCOMING→ACTIVE/ARCHIVED) |
| `check_and_send_messages()` | :20, :50 | Анонсы (≤5 дней), стартовые (≤12ч), уведомления подписчикам (старт/экватор/за 2 дня до конца) |
| `update_game_states()` | :05, :35 | Обновляет статусы по времени (пропускает COMPLETED от парсера) |

### Глобальные объекты (`loader.py`)

Все DAO и бот создаются один раз и импортируются из `loader.py`:

```python
bot, dp, db, game_dao, user_dao, user_subs_dao, user_role_dao
```

### Database Layer (SQLAlchemy + asyncpg)

**Модели** (`db/models.py`):

- `GameDate` — игра со статусами: UPCOMING(0) → ACTIVE(1) → COMPLETED(2) / ARCHIVED(3)
- `User` — пользователь (telegram_id: BigInteger, bot_blocked)
- `UserGameSubscription` — M2M подписки (+ флаги уведомлений: equator, 2days_before_end, game_started)
- `UserGameRole` — M2M поиск команды (role: "Команда" / "Игрок")

**DAO** (`db/dao/`):

- `BaseDAO` — generic CRUD, принимает `async_sessionmaker` (не session). Фильтры Django-style: `__gte`, `__lte`, `__eq`, `order_by`
- `GameDateDAO.create()` — upsert-логика: при обновлении дат сбрасывает флаги анонсов (если сдвиг ≥5 дней), скачивает изображения, отправляет уведомления об изменении дат

Каждый метод DAO создаёт сессию через `async with self.session_factory() as session`.

### Parser (`parser/`)

- `parser.py` — два режима: upcoming (`GAMES_URLS`) и active (`ACTIVE_GAMES_URLS`). Парсит HTML-таблицы с Encounter, поддерживает пагинацию и зеркала (.encounter.cx → .en.cx → .encounter.ru)
- `schemas.py` — Pydantic-модели `GameDate` и `AdditionalData`. Валидация дат с переводом русских месяцев. Ссылка на игру генерируется автоматически из domain + id
- `utils.py` — `download_image()` скачивает обложки в `images/{game_id}.{ext}`

### Handlers (`handlers/main_handlers.py`)

Команды: `/start`, `/upcoming`, `/active`, `/actives`, `/subs`, `/help`. Все (кроме /help в группах) фильтруются через `PrivateChatFilter()` и декоратор `@ensure_user_registered`.

Callback-обработчики: `SubscribeCallbackData` (личные подписки), `SubscribeFromChannelCallbackData` (подписка из канала, авто-создание пользователя), `GameRoleCallbackData` (поиск команды/игрока).

### Messages (`messages/`)

- `messages.py` — форматирование сообщений, отправка анонсов/стартовых/уведомлений об изменении дат в `CHATS_ID`, личные уведомления подписчикам
- `scheduler_messages.py` — оркестрация: `check_and_send_messages()` вызывает анонсы + стартовые + уведомления подписчикам (окно 1 час для cron-задач каждые 30 мин)

## Critical Implementation Details

### URL-преобразование

Парсер хранит `.encounter.cx`, пользователю показывается `.en.cx` через `get_user_facing_link()`. Функция дублируется в `handlers/main_handlers.py` и `messages/messages.py`.

### Timezone

Все операции — Moscow TZ (`Europe/Moscow`). БД хранит naive datetime; Python сравнивает после `datetime.now(moscow_tz).replace(tzinfo=None)`.

### Изображения

Хранятся как `images/{game_id}.{extension}`. `GameDate.image` — локальный путь, `GameDate.image_url` — оригинальный URL. Fallback — `images/DEFAULT.jpg`. Паттерн получения пути:

```python
file_name = str(game.id) + '.' + game.image.split('.')[-1] if game.image else None
photo_path = Path(f"images/{file_name}").resolve()
if not photo_path.exists() or not photo_path.is_file():
    photo_path = Path("images/DEFAULT.jpg").resolve()
```

### Game State Transitions

1. Парсер создаёт как UPCOMING
2. `update_game_states()` — UPCOMING→ACTIVE (по start_date), ACTIVE→COMPLETED (по end_date). Пропускает уже COMPLETED
3. `parsing_active_games()` — ACTIVE→COMPLETED (исчезла с сайта), UPCOMING→ACTIVE (найдена в активных), UPCOMING→ARCHIVED (исчезла отовсюду)
4. При COMPLETED удаляются подписки и роли

### Защита от ложных срабатываний парсера

- Если >10 игр на COMPLETED или >10 на ACTIVE за раз — предупреждение в лог
- Архивирование только если ≤5 игр за раз
- При ошибке загрузки активных игр — пропуск всего цикла обновления

## CI/CD

GitHub Actions (`.github/workflows/action.yml`): push в `main` → Docker build → push в Docker Hub (`alexeygalt/enc_bot`) → деплой на сервер через SSH (docker compose up -d). Секреты: DB_*, BOT_TOKEN, CHATS_ID, DOCKER_TOKEN, HOST, SSH_USERNAME, SSH_PASSWORD.

## Rules

### Role

You are a Senior Developer with a deep understanding of best practices and performance optimization techniques. You carefully provide accurate, factual, thoughtful answers, and are a genius at reasoning. At the same time, you are strict, laconic and critical.

### General

- Before you propose a solution to a problem, make sure you have sufficient context.
- Concise Code: Be concise and minimize any other prose.
- No Guessing: If you think there might not be a correct answer, you say so. If you do not know the answer, say so, instead of guessing and don't lie.
- Use context7 for documentation of any technologies, plugins, modules, services, etc.
- Don't make any improvements or write unnecessary code yourself unless it was planned. If there's any deviation from the plan, ask questions. Instead of initiating the writing of unnecessary code, prefer to suggest writing it if you see the point.
- При ответах всегда используй русский язык.

### Code Style and Structure

- Use functional and declarative programming patterns; avoid classes.
- Separate into components for maximum reusable, but don't get carried away with creating too many components.
- Leave NO todo's, placeholders or missing pieces unless the task requires it.
- Use modern best coding techniques, practices and patterns.

### Basic principles of implementation

If the project structure allows, the implementation must strictly adhere to these non-negotiable principles:

- YAGNI (You Aren't Gonna Need It)
- KISS (Keep It Simple, Stupid)
- DRY (Don't Repeat Yourself)
- SOLID Principles (Single-responsibility principle, Open–closed principle, Liskov substitution principle, Interface segregation principle, Dependency inversion principle)

Always follow the YAGNI + KISS + DRY + SOLID principles when designing or adding new code, If appropriate. If the codebase and project structure do not allow for any of these principles, they can be ignored, but should be communicated.

### How to ensure "Always Works" implementation

Follow this systematic approach:

#### Core Philosophy

- "Should work" ≠ "does work" - Pattern matching isn't enough
- I'm not paid to write code, I'm paid to solve problems
- Untested code is just a guess, not a solution

#### The 30-Second Reality Check - Must answer YES to ALL

- Did I run/build the code?
- Did I trigger the exact feature I changed?
- Did I see the expected result with my own observation (including GUI)?
- Did I check for error messages?
- Would I bet $100 this works?

#### Phrases to Avoid

- "This should work now"
- "I've fixed the issue" (especially 2nd+ time)
- "Try it now" (without trying it myself)
- "The logic is correct so..."

#### Specific Test Requirements

- UI Changes: Actually click the button/link/form
- API Changes: Make the actual API call
- Data Changes: Query the database
- Logic Changes: Run the specific scenario
- Config Changes: Restart and verify it loads

#### The Embarrassment Test

"If the user records trying this and it fails, will I feel embarrassed to see his face?"

#### Time Reality

- Time saved skipping tests: 30 seconds
- Time wasted when it doesn't work: 30 minutes
- User trust lost: Immeasurable

A user describing a bug for the third time isn't thinking "this AI is trying hard" - they're thinking "why am I wasting time with this incompetent tool?"

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot for tracking and announcing Encounter games (Encounter.cx platform). The bot:

- Scrapes game data from Encounter websites on a schedule
- Sends announcements to Telegram channels/groups about upcoming games
- Allows users to subscribe to games and find teammates
- Tracks game states (UPCOMING → ACTIVE → COMPLETED → ARCHIVED)
- Manages user subscriptions and team search functionality

## Development Commands

### Running the Bot

**Local development:**

```bash
python main.py
```

**Docker deployment:**

```bash
docker-compose up --build
```

The bot runs migrations automatically on startup via the entrypoint command:

```bash
alembic upgrade head && python main.py
```

### Database Migrations

**Create a new migration:**

```bash
alembic revision --autogenerate -m "description"
```

**Apply migrations:**

```bash
alembic upgrade head
```

**Rollback migration:**

```bash
alembic downgrade -1
```

Migration files are located in `db/migrations/versions/`. The migration environment (`db/migrations/env.py`) automatically loads models from `db/models.py` and uses the `DATABASE_URL` from `settings.py`.

## Architecture

### Core Components Flow

main.py (entry point)
  ├─ Initializes bot, dispatcher, and database (from loader.py)
  ├─ Sets up APScheduler with Moscow timezone
  ├─ Registers handlers from handlers/main_handlers.py
  └─ Runs 4 scheduled jobs:
      ├─ run_parsing() - Every :15 and :45 (parses upcoming games)
      ├─ parsing_active_games() - Every :55 (parses active games, updates states)
      ├─ check_and_send_messages() - Every :20 and :50 (sends announcements/start messages)
      └─ update_game_states() - Every :05 and :35 (updates game states based on time)

### Database Layer (SQLAlchemy + asyncpg)

**Models** (`db/models.py`):

- `GameDate` - Game information with states (UPCOMING=0, ACTIVE=1, COMPLETED=2, ARCHIVED=3)
- `User` - Telegram users (telegram_id as BigInteger)
- `UserGameSubscription` - M2M for user subscriptions to games
- `UserGameRole` - M2M for team search (role: "Команда" or "Игрок")

**DAO Pattern** (`db/dao/`):

- `BaseDAO` - Generic CRUD with filter operators (`__gte`, `__lte`, `__eq`)
- `GameDateDAO` - Overrides `create()` to handle upserts, date change notifications, and image downloads
- `UserDAO`, `UserGameSubscriptionDAO`, `UserGameRoleDAO` - Specific DAOs for other models

**Database Manager** (`db/manager.py`):

- `DatabaseManager` - Creates async engine and session factory
- Instantiated in `loader.py` with `DATABASE_URL` from settings

### Parser System (`parser/`)

**Two parsing modes:**

1. **Upcoming games** (`run_parsing()`):
   - Scrapes from `GAMES_URLS` (team/single games with status=Coming)
   - Creates/updates games via `GameDateDAO.create()` which handles upserts
   - Downloads images to `images/` directory named as `{game_id}.{ext}`

2. **Active games** (`parsing_active_games()`):
   - Scrapes from `ACTIVE_GAMES_URLS` (status=Active)
   - Compares parsed games with DB state to detect state transitions:
     - Games that disappeared from "active" → COMPLETED
     - Games that disappeared from "upcoming" → ACTIVE (or ARCHIVED if not found in active)
   - Updates game fields (name, dates, images) for still-active games
   - Deletes subscriptions/roles when games move to COMPLETED

**Key functions:**

- `fetch_html()` - Async HTTP fetching with aiohttp
- `parse_game_data()` - Extracts game rows from HTML tables
- `gather_additional_game_data()` - Fetches game detail pages for end_date, max_players, images
- `download_image()` (`parser/utils.py`) - Downloads and saves game images

### Message System (`messages/`)

**Scheduled announcements:**

- `send_announcement_messages()` - Sends to `CHATS_ID` when start_date ≤ now + 5 days
- `send_start_messages()` - Sends to `CHATS_ID` when start_date ≤ now + 12 hours
- `send_game_message_date_change()` - Notifies subscribers when dates change

All messages use photos from `images/{game_id}.{ext}` or fallback to `images/DEFAULT.jpg`.

### Handlers (`handlers/main_handlers.py`)

**Commands:**

- `/start` - Register user (requires username)
- `/upcoming` - List upcoming games with subscribe buttons
- `/active` - List active games
- `/actives` - Compact list of active games (no images)
- `/subs` - User's subscribed games with team search
- `/help` - Command list

**Callback handlers:**

- `SubscribeCallbackData` - Subscribe/unsubscribe to games
- `SubscribeFromChannelCallbackData` - Subscribe from channel posts (auto-creates user)
- `GameRoleCallbackData` - Team search (find_player/find_team/cancel_search/back_to_main)

### Settings (`settings.py`)

Uses `pydantic.v1.BaseSettings` to load from `.env`:

- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_NAME` → PostgreSQL connection
- `BOT_TOKEN` → Telegram bot token
- `CHATS_ID` → Comma-separated chat IDs for announcements

**Properties:**

- `get_database_url` → Returns `postgresql+asyncpg://...`
- `get_chat_ids` → Splits `CHATS_ID` into list

### Logging (`logging_config.py`)

Creates three loggers:

- `bot_logger` - Bot operations
- `parser_logger` - Parsing operations
- `db_logger` - Database operations

All write to `logs/logs.log` with rotation.

## Important Implementation Details

### Game State Management

Games transition through states automatically:

1. Parser creates games as UPCOMING (default)
2. `update_game_states()` moves UPCOMING → ACTIVE when start_date passes
3. `parsing_active_games()` moves ACTIVE → COMPLETED when no longer on website
4. Parser can ARCHIVE upcoming games that disappeared from website

**Critical:** `update_game_states()` skips games already COMPLETED by parser to avoid conflicts.

### Image Handling

- Images are downloaded in `parser/utils.py:download_image()`
- Stored as `images/{game_id}.{extension}`
- `GameDate.image` stores local path, `GameDate.image_url` stores original URL
- Always check `photo_path.exists()` before sending - fallback to `images/DEFAULT.jpg`

### Date Change Notifications

When `GameDateDAO.create()` detects date changes:

- If start_date changed by ≥5 days: reset `is_announcement_sent` and `is_start_message_sent`
- If game already announced: send change notification via `send_game_message_date_change()`
- Supports three message types: "reschedule_start", "reschedule_end", "both_reschedule"

### URL Handling

The codebase stores `.encounter.cx` URLs internally but displays `.en.cx` to users:

- Parser stores: `domain.replace('.en.cx', '.encounter.cx')`
- Display: `get_user_facing_link()` converts back to `.en.cx`

### Session Management

All DAOs receive `async_sessionmaker` (not `AsyncSession`):

```python
# In loader.py
db = DatabaseManager(DATABASE_URL)
game_dao = GameDateDAO(db.async_session)  # Pass sessionmaker, not session

# In DAO methods
async with self.session_factory() as session:  # Create session per operation
    # ... use session
```

### Timezone Handling

All time operations use Moscow timezone (`Europe/Moscow`):

```python
moscow_tz = pytz.timezone('Europe/Moscow')
now = datetime.now(moscow_tz).replace(tzinfo=None)  # Remove tzinfo for DB comparison
```

Database stores naive datetimes; Python compares as naive after TZ conversion.

## Common Patterns

### Adding a New Scheduled Job

In `main.py`:

```python
scheduler.add_job(
    your_function,
    CronTrigger(minute="*/30"),  # Every 30 minutes
    args=[arg1, arg2]
)
```

### Adding a New Command Handler

1. Add to `handlers/main_handlers.py`:

```python
@router.message(Command(commands='yourcommand'), PrivateChatFilter())
@ensure_user_registered(user_dao)
async def your_command(message: Message):
    # Implementation
```

2. Update `keyboards/constants.py` with command description

### Working with Game Images

Always use this pattern:

```python
file_name = str(game.id) + '.' + game.image.split('.')[-1] if game.image else None
photo_path = Path(f"images/{file_name}").resolve()
if not photo_path.exists() or not photo_path.is_file():
    bot_logger.info(f"❌ Файл {photo_path} не найден. Используем изображение по умолчанию.")
    photo_path = Path("images/DEFAULT.jpg").resolve()
```

### DAO Filtering

BaseDAO supports Django-style filters:

```python
# Exact match
games = await game_dao.get_all(state=GameState.ACTIVE.value)

# Comparison operators
games = await game_dao.get_all(
    start_date__lte=future_date,
    is_announcement_sent=False,
    order_by="start_date"
)
```

## Testing Notes

- No test suite currently exists
- Manual testing via Docker: `docker-compose up`
- Check `logs/logs.log` for parsing/bot errors
- Database is PostgreSQL 15 (see `docker-compose.yaml`)

## Rules

### Role

You are a Senior Developer with a deep understanding of best practices and performance optimization techniques. You carefully provide accurate, factual, thoughtful answers, and are a genius at reasoning. At the same time, you are strict, laconic and critical.

### General

- Before you propose a solution to a problem, make sure you have sufficient context.
- Concise Code: Be concise and minimize any other prose.
- No Guessing: If you think there might not be a correct answer, you say so. If you do not know the answer, say so, instead of guessing and don't lie.
- Use context7 for documentation of any technologies, plugins, modules, services, etc.
- Don't make any improvements or write unnecessary code yourself unless it was planned. If there's any deviation from the plan, ask questions. Instead of initiating the writing of unnecessary code, prefer to suggest writing it if you see the point.
- Контекст будет автоматически сжиматься по мере приближения к лимиту. Никогда не останавливай задачу из-за ограничений токенов. Всегда доводи её до конца, даже если бюджет почти исчерпан.
- При ответах всегда используй русский язык.

### Code Style and Structure

- Use functional and declarative programming patterns; avoid classes.
- Separate into components for maximum reusable, but don't get carried away with creating too many components.
- Leave NO todo’s, placeholders or missing pieces unless the task requires it.
- Use modern best coding techniques, practices and patterns.
- Use FSD architecture if it is appropriate for the project after reviewing it. Suitable only for creating new projects.
- Document code with JSDoc comments.

### Basic principles of implementation

If the project structure allows, the implementation must strictly adhere to these non-negotiable principles:

- YAGNI (You Aren't Gonna Need It)
- KISS (Keep It Simple, Stupid)
- DRY (Don't Repeat Yourself)
- SOLID Principles (Single-responsibility principle, Open–closed principle, Liskov substitution principle, Interface segregation principle, Dependency inversion principle)

Always follow the YAGNI + KISS + DRY + SOLID principles when designing or adding new code, If appropriate. If the codebase and project structure do not allow for any of these principles, they can be ignored, but should be communicated.

### How to ensure "Always Works" implementation

Please ensure your implementation Always Works™ for this project tasks.

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
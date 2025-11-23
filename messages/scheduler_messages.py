from datetime import datetime, timedelta
import pytz

from logging_config import bot_logger
from messages.messages import send_announcement_messages, send_start_messages, send_subscriber_notification
from db.models import GameState


async def send_subscriber_notifications(game_dao, user_subs_dao, user_dao, bot):
    """Отправляет личные уведомления подписчикам ACTIVE игр"""
    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow_tz).replace(tzinfo=None)

    active_games = await game_dao.get_all(state=GameState.ACTIVE.value)

    for game in active_games:
        if not game.end_date:
            continue

        game_duration = game.end_date - game.start_date
        equator_time = game.start_date + (game_duration / 2)
        two_days_before_end = game.end_date - timedelta(days=2)

        # ОКНО 1 ЧАС (для задачи каждые 30 мин гарантирует попадание)
        window = timedelta(hours=1)

        # 1. Уведомление при старте
        if game.start_date <= now < game.start_date + window:
            subscribers = await user_subs_dao.get_subscriptions_for_notification(game.id, "game_started")
            for sub in subscribers:
                success = await send_subscriber_notification(
                    bot, sub["telegram_id"], sub["user_id"], game, "game_started", user_dao
                )
                if success:
                    await user_subs_dao.update_notification_flag(
                        sub["user_id"], game.id, "is_game_started_notified", True
                    )

        # 2. Уведомление на экваторе
        if equator_time <= now < equator_time + window:
            subscribers = await user_subs_dao.get_subscriptions_for_notification(game.id, "equator")
            for sub in subscribers:
                success = await send_subscriber_notification(
                    bot, sub["telegram_id"], sub["user_id"], game, "equator", user_dao
                )
                if success:
                    await user_subs_dao.update_notification_flag(
                        sub["user_id"], game.id, "is_equator_notified", True
                    )

        # 3. За 2 дня (только если не дублирует экватор и игра длится >= 2 суток)
        if two_days_before_end > game.start_date and two_days_before_end <= now < two_days_before_end + window:
            if (two_days_before_end - equator_time).total_seconds() >= 3600:
                subscribers = await user_subs_dao.get_subscriptions_for_notification(game.id, "2days_before_end")
                for sub in subscribers:
                    success = await send_subscriber_notification(
                        bot, sub["telegram_id"], sub["user_id"], game, "2days_before_end", user_dao
                    )
                    if success:
                        await user_subs_dao.update_notification_flag(
                            sub["user_id"], game.id, "is_2days_before_end_notified", True
                        )


async def check_and_send_messages(game_dao, user_subs_dao, user_dao, bot):
    """Проверка и отправка ВСЕХ уведомлений (анонсы + подписчики)"""
    await send_announcement_messages(game_dao, bot)
    await send_start_messages(game_dao, bot)
    await send_subscriber_notifications(game_dao, user_subs_dao, user_dao, bot)
    bot_logger.info("All game messages processed and updated.")

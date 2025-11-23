from sqlalchemy import select, update

from db.dao.base import BaseDAO
from db.models import UserGameSubscription, UserGameRole, User, GameDate


class UserGameSubscriptionDAO(BaseDAO):
    __model__ = UserGameSubscription

    async def add_user_to_subscription(self, user_id: int, game_id: int):
        async with self.session_factory() as session:
            existing_user = await session.execute(
                select(User).filter_by(telegram_id=user_id)
            )
            user = existing_user.scalars().first()

            existing_game = await session.execute(
                select(GameDate).filter_by(id=game_id)
            )
            game = existing_game.scalars().first()

            if not game:
                return f"Упс {game_id} уже не существует."

            existing_subscription = await self.get(user_id=user.id, game_id=game_id)

            if existing_subscription:
                return f"Вы уже подписаны на игру {game_id}."

            await self.create(user_id=user.id, game_id=game_id)
            return f"Вы успешно подписались на игру {game_id}."

    async def remove_user_from_subscription(self, user_id: int, game_id: int):
        """Удаляет подписку пользователя на игру"""
        async with self.session_factory() as session:
            existing_user = await session.execute(
                select(User).filter_by(telegram_id=user_id)
            )
            user = existing_user.scalars().first()

            existing_subscription = await self.get(user_id=user.id, game_id=game_id)
            if not existing_subscription:
                return f"Вы не подписаны на игру {game_id}."

            await self.delete(user_id=user.id, game_id=game_id)
            return f"Вы успешно отписались от игры {game_id}."

    async def is_user_subscribed(self, user_id: int, game_id: int) -> bool:
        """Проверяет, подписан ли пользователь на игру"""
        async with self.session_factory() as session:
            existing_user = await session.execute(
                select(User).filter_by(telegram_id=user_id)
            )
            user = existing_user.scalars().first()

            if not user:
                return False

            existing_subscription = await self.get(user_id=user.id, game_id=game_id)
            return existing_subscription is not None

    async def update_notification_flag(
        self,
        user_id: int,  # Внутренний id из users.id
        game_id: int,
        flag_name: str,
        value: bool
    ) -> None:
        """Обновляет флаг уведомления для подписки"""
        async with self.session_factory() as session:
            stmt = update(UserGameSubscription).where(
                UserGameSubscription.user_id == user_id,
                UserGameSubscription.game_id == game_id
            ).values({flag_name: value})
            await session.execute(stmt)
            await session.commit()

    async def get_subscriptions_for_notification(
        self,
        game_id: int,
        notification_type: str
    ) -> list[dict]:
        """Возвращает подписчиков для уведомления (фильтрует по bot_blocked и флагу)"""
        async with self.session_factory() as session:
            flag_map = {
                "equator": UserGameSubscription.is_equator_notified,
                "2days_before_end": UserGameSubscription.is_2days_before_end_notified,
                "game_started": UserGameSubscription.is_game_started_notified
            }

            stmt = (
                select(
                    User.id.label("user_id"),
                    User.telegram_id,
                    User.nickname,
                    UserGameSubscription.is_equator_notified,
                    UserGameSubscription.is_2days_before_end_notified,
                    UserGameSubscription.is_game_started_notified
                )
                .join(User, UserGameSubscription.user_id == User.id)
                .where(
                    UserGameSubscription.game_id == game_id,
                    User.bot_blocked == False,
                    flag_map[notification_type] == False
                )
            )

            result = await session.execute(stmt)
            return [dict(row) for row in result.mappings().all()]

    async def reset_notification_flags_for_game(self, game_id: int) -> None:
        """Сбрасывает все флаги уведомлений для всех подписчиков игры"""
        async with self.session_factory() as session:
            stmt = update(UserGameSubscription).where(
                UserGameSubscription.game_id == game_id
            ).values({
                "is_equator_notified": False,
                "is_2days_before_end_notified": False,
                "is_game_started_notified": False
            })
            await session.execute(stmt)
            await session.commit()


class UserGameRoleDAO(BaseDAO):
    __model__ = UserGameRole

    async def add_user_role(self, user_id: int, game_id: int, role: str):
        """Добавляет или обновляет роль пользователя в игре"""
        async with self.session_factory() as session:
            existing_user = await session.execute(
                select(User).filter_by(telegram_id=user_id)
            )
            user = existing_user.scalars().first()

            if not user:
                return "Ошибка: Пользователь не найден."

            existing_game = await session.execute(
                select(GameDate).filter_by(id=game_id)
            )
            game = existing_game.scalars().first()

            if not game:
                return f"Упс {game_id} уже не существует."

            existing_role = await self.get(user_id=user.id, game_id=game_id)

            if existing_role:
                existing_role.role = role
                await session.commit()
                return
            await self.create(user_id=user.id, game_id=game_id, role=role)
            return

    async def get_opposite_role_users(self, game_id: int, opposite_role: str):
        """Возвращает список пользователей с противоположной ролью"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(User.nickname)
                .join(UserGameRole, User.id == UserGameRole.user_id)
                .filter(UserGameRole.game_id == game_id, UserGameRole.role == opposite_role)
            )
            return [row[0] for row in result.fetchall()]

    async def get_opposite_role_users_count(self, game_id: int, opposite_role: str):
        """Возвращает количество пользователей с противоположной ролью"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(User.id)
                .join(UserGameRole, User.id == UserGameRole.user_id)
                .filter(UserGameRole.game_id == game_id, UserGameRole.role == opposite_role)
            )

            users = result.scalars().all()
            return len(users)

    async def is_user_searching(self, user_id: int, game_id: int) -> bool:
        """Проверяет, ищет ли пользователь игрока или команду в игре"""
        async with self.session_factory() as session:
            existing_user = await session.execute(
                select(User).filter_by(telegram_id=user_id)
            )
            user = existing_user.scalars().first()

            if not user:
                return False
            existing_search = await self.get(user_id=user.id, game_id=game_id)

            if existing_search:
                return True
            return False

from sqlalchemy import select

from db.dao.base import BaseDAO
from db.models import UserGameSubscription, UserGameRole, User, GameDate


class UserGameSubscriptionDAO(BaseDAO):
    __model__ = UserGameSubscription

    async def add_user_to_subscription(self, user_id: int, game_id: int):
        existing_user = await self.session.execute(
            select(User).filter_by(telegram_id=user_id)
        )
        user = existing_user.scalars().first()

        existing_game = await self.session.execute(
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
        existing_user = await self.session.execute(
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
        existing_user = await self.session.execute(
            select(User).filter_by(telegram_id=user_id)
        )
        user = existing_user.scalars().first()

        if not user:
            return False

        existing_subscription = await self.get(user_id=user.id, game_id=game_id)
        return existing_subscription is not None


class UserGameRoleDAO(BaseDAO):
    __model__ = UserGameRole

    async def add_user_role(self, user_id: int, game_id: int, role: str):
        """Добавляет или обновляет роль пользователя в игре"""
        existing_user = await self.session.execute(
            select(User).filter_by(telegram_id=user_id)
        )
        user = existing_user.scalars().first()

        if not user:
            return "Ошибка: Пользователь не найден."

        existing_game = await self.session.execute(
            select(GameDate).filter_by(id=game_id)
        )
        game = existing_game.scalars().first()

        if not game:
            return f"Упс {game_id} уже не существует."

        existing_role = await self.get(user_id=user.id, game_id=game_id)

        if existing_role:
            existing_role.role = role
            await self.session.commit()
            return
        await self.create(user_id=user.id, game_id=game_id, role=role)
        return

    async def get_opposite_role_users(self, game_id: int, opposite_role: str):
        """Возвращает список пользователей с противоположной ролью"""
        async with self.session as session:
            result = await session.execute(
                select(User.nickname)
                .join(UserGameRole, User.id == UserGameRole.user_id)
                .filter(UserGameRole.game_id == game_id, UserGameRole.role == opposite_role)
            )
            return [row[0] for row in result.fetchall()]

    async def get_opposite_role_users_count(self, game_id: int, opposite_role: str):
        """Возвращает количество пользователей с противоположной ролью"""
        async with self.session as session:
            result = await session.execute(
                select(User.id)
                .join(UserGameRole, User.id == UserGameRole.user_id)
                .filter(UserGameRole.game_id == game_id, UserGameRole.role == opposite_role)
            )

            users = result.scalars().all()
            return len(users)

    async def is_user_searching(self, user_id: int, game_id: int) -> bool:
        """Проверяет, ищет ли пользователь игрока или команду в игре"""
        existing_user = await self.session.execute(
            select(User).filter_by(telegram_id=user_id)
        )
        user = existing_user.scalars().first()

        if not user:
            return False
        existing_search = await self.get(user_id=user.id, game_id=game_id)

        if existing_search:
            return True
        return False

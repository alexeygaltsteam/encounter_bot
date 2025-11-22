from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class BaseDAO:
    __model__ = None

    def __init__(self, session_factory):
        # session_factory — async_sessionmaker
        self.session_factory = session_factory

    async def create(self, **kwargs):
        async with self.session_factory() as session:
            instance = self.__model__(**kwargs)
            session.add(instance)
            await session.commit()
            return instance

    async def get(self, **kwargs):
        async with self.session_factory() as session:
            stmt = select(self.__model__).filter_by(**kwargs)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_all(self, order_by=None, **kwargs):
        async with self.session_factory() as session:
            stmt = select(self.__model__)

            filter_map = {
                '__gte': lambda column, value: column >= value,
                '__lte': lambda column, value: column <= value,
                '__eq': lambda column, value: column == value,
            }

            for key, value in kwargs.items():
                for suffix, condition in filter_map.items():
                    if key.endswith(suffix):
                        column_name = key.replace(suffix, '')
                        column = getattr(self.__model__, column_name)
                        stmt = stmt.filter(condition(column, value))
                        break

                else:
                    column = getattr(self.__model__, key)
                    stmt = stmt.filter(column == value)

            if order_by:
                stmt = stmt.order_by(getattr(self.__model__, order_by))

            result = await session.execute(stmt)
            return result.scalars().all()

    async def update(self, **kwargs):
        async with self.session_factory() as session:
            instance = await self.get(**kwargs)
            if instance:
                await session.execute(update(self.__model__).where(
                    *[getattr(self.__model__, key) == value for key, value in kwargs.items()]
                ))
                await session.commit()

    async def delete(self, **kwargs):
        async with self.session_factory() as session:
            stmt = select(self.__model__).filter_by(**kwargs)
            result = await session.execute(stmt)
            instance = result.scalars().first()
            if instance:
                await session.delete(instance)
                await session.commit()


from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class BaseDAO:
    __model__ = None

    def __init__(self, session: AsyncSession):
        self.session = session()

    async def create(self, **kwargs):
        instance = self.__model__(**kwargs)
        self.session.add(instance)
        await self.session.commit()
        return instance

    async def get(self, **kwargs):
        stmt = select(self.__model__).filter_by(**kwargs)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all(self, order_by=None, **kwargs):
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

        result = await self.session.execute(stmt)
        await self.session.close()
        return result.scalars().all()

    async def update(self, **kwargs):
        instance = await self.get(**kwargs)
        if instance:
            await self.session.execute(update(self.__model__).where(
                *[getattr(self.__model__, key) == value for key, value in kwargs.items()]
            ))
            await self.session.commit()

    async def delete(self, **kwargs):
        stmt = select(self.__model__).filter_by(**kwargs)
        result = await self.session.execute(stmt)
        instance = result.scalars().first()
        if instance:
            await self.session.delete(instance)
            await self.session.commit()


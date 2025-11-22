from db.dao.base import BaseDAO
from db.models import GameDate
from messages.messages import send_game_message_date_change
from logging_config import parser_logger
from parser.utils import download_image


class GameDateDAO(BaseDAO):
    __model__ = GameDate

    async def create(self, **kwargs):
        from loader import bot
        existing_instance = await self.session.get(self.__model__, kwargs.get('id'))

        if existing_instance:
            new_end_date = kwargs.get('end_date')
            new_start_date = kwargs.get('start_date')
            old_end_date = existing_instance.end_date
            old_start_date = existing_instance.start_date

            start_date_updated = new_start_date and new_start_date != old_start_date
            end_date_updated = new_end_date and new_end_date != old_end_date

            if start_date_updated and (new_start_date - old_start_date).days >= 5:
                existing_instance.is_announcement_sent = False
                existing_instance.is_start_message_sent = False

            if start_date_updated:
                existing_instance.start_date = new_start_date
            if end_date_updated:
                existing_instance.end_date = new_end_date

            for key, value in kwargs.items():
                if hasattr(existing_instance, key) and key not in ('id', 'start_date', 'end_date'):
                    if key == "image" and isinstance(value, str) and value.startswith("http"):
                        # Сравниваем с оригинальным URL, а не с локальным путём
                        current_image_url = getattr(existing_instance, 'image_url', None)
                        if current_image_url != value:
                            download_result = await download_image(value, game_id=existing_instance.id)

                            if download_result is not None:
                                # Сохраняем локальный путь в image и оригинальный URL в image_url
                                existing_instance.image = download_result
                                existing_instance.image_url = value
                                parser_logger.info(f"Изображение изменено для : {kwargs.get('id')}")
                                parser_logger.info(f"  Старый URL: {current_image_url}")
                                parser_logger.info(f"  Новый URL: {value}")
                            else:
                                existing_instance.image = None
                                existing_instance.image_url = value
                                parser_logger.info(
                                    f"❌ Изображение не было загружено, ставим None для : {kwargs.get('id')}")
                    else:
                        setattr(existing_instance, key, value)

            self.session.add(existing_instance)
            if start_date_updated or end_date_updated:
                parser_logger.info(f"Объект обновлен: {kwargs.get('id')}")
                if existing_instance.is_announcement_sent:
                    if start_date_updated and end_date_updated:
                        await send_game_message_date_change(
                            bot=bot,
                            game=existing_instance,
                            message_type="both_reschedule",
                            new_start_date=new_start_date,
                            old_start_date=old_start_date,
                            new_end_date=new_end_date,
                            old_end_date=old_end_date,
                        )
                    elif start_date_updated:
                        await send_game_message_date_change(
                            bot=bot,
                            game=existing_instance,
                            message_type="reschedule_start",
                            new_start_date=new_start_date,
                            old_start_date=old_start_date,
                        )
                    elif end_date_updated:
                        await send_game_message_date_change(
                            bot=bot,
                            game=existing_instance,
                            message_type="reschedule_end",
                            new_end_date=new_end_date,
                            old_end_date=old_end_date,
                        )
                    # existing_instance.is_announcement_sent = False
                    # existing_instance.is_start_message = False

            await self.session.commit()

        else:
            # Сохраняем оригинальный URL изображения
            original_image_url = kwargs.get('image')
            instance = self.__model__(**kwargs)
            self.session.add(instance)
            parser_logger.info(f"Создан новый объект: {kwargs.get('id')}")

            # Скачиваем изображение, если URL предоставлен
            if original_image_url and isinstance(original_image_url, str) and original_image_url.startswith("http"):
                download_result = await download_image(image_url=original_image_url, game_id=instance.id)
                if download_result is None:
                    parser_logger.info(f"❌ Не удалось загрузить изображение для {kwargs.get('id')}. Устанавливаем None.")
                    instance.image = None
                else:
                    instance.image = download_result
                instance.image_url = original_image_url
            await self.session.commit()

        await self.session.close()

import re
import os
import aiohttp
import aiofiles

from logging_config import parser_logger


def extract_limit(text: str) -> int:
    match = re.search(r'\d+', text)
    if match:
        return int(match.group(0))
    return 0


async def download_image(image_url, game_id, save_dir="images"):
    """Асинхронно загружает изображение по ссылке и сохраняет его локально."""
    os.makedirs(save_dir, exist_ok=True)

    if not image_url or not image_url.startswith(("http://", "https://")):
        parser_logger.info(f"❌ Ошибка: Неверный URL -> {image_url}")
        return None

    # file_name = image_url.split("/")[-1]
    # file_path = os.path.join(save_dir, file_name)
    file_name = str(game_id) + '.' + image_url.split('.')[-1]
    file_path = os.path.join(save_dir, file_name)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    async with aiofiles.open(file_path, "wb") as file:
                        await file.write(await response.read())
                    parser_logger.info(f"✅ Изображение сохранено: {file_path}")
                    return file_path
                else:
                    parser_logger.info(f"❌ Ошибка загрузки: {response.status}")
                    return None
    except aiohttp.ClientError as e:
        parser_logger.info(f"⚠️ Ошибка при загрузке: {e}")
        return None


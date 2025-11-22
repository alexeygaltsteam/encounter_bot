from typing import Optional, List
import aiohttp
import asyncio
import re
from bs4 import BeautifulSoup
from sqlalchemy import update, delete

from db.models import GameState, GameDate as GameModel, UserGameSubscription, UserGameRole
from loader import game_dao
from .schemas import GameDate, AdditionalData
from .utils import extract_limit, download_image
from logging_config import parser_logger

GAMES_URLS = [
    ("https://kovrov.encounter.cx/GameCalendar.aspx?status=Coming&type=Team&zone=Virtual", "team"),
    ("https://kovrov.encounter.cx/GameCalendar.aspx?status=Coming&type=Single&zone=Virtual", "single")
]

ACTIVE_GAMES_URLS = [
    ("https://arcticsearch.encounter.cx/GameCalendar.aspx?status=Active&type=Team&zone=Virtual", "team"),
    ("https://arcticsearch.encounter.cx/GameCalendar.aspx?status=Active&type=Single&zone=Virtual", "single")
]

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html",
    "Accept-Language": "en-US",
}


async def fetch_html(session: aiohttp.ClientSession, url: str, headers: Optional[dict] = None) -> Optional[str]:
    """
        Асинхронно получает HTML-страницу по заданному URL.

        :param session: Объект aiohttp.ClientSession.
        :param url: URL для загрузки.
        :param headers: HTTP-заголовки запроса.
        :return: Текст HTML или None при ошибке.
    """
    headers = headers or DEFAULT_HEADERS
    try:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            return await response.text()
    except Exception as e:
        parser_logger.error(f"Ошибка при загрузке {url}: {e}")
        return None


def extract_pagination_links(html: str) -> List[str]:
    """
        Извлекает ссылки пагинации из HTML.

        :param html: Текст HTML.
        :return: Список ссылок.
    """
    soup = BeautifulSoup(html, "html.parser")
    pagination_td = soup.find('td', align="left")
    return [a['href'] for a in pagination_td.find_all('a', href=True)] if pagination_td else []


async def parse_game_data(html: str, game_type: str) -> List[GameDate]:
    """
        Парсит данные игр из HTML.

        :param html: Текст HTML.
        :param game_type: Тип игры (team или single).
        :return: Список объектов GameDate.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr", id=lambda x: x and x.startswith("ctl20_ctl00_GamesRepeater"))

    games = []
    for row in rows:
        cells = row.find_all("td")
        row_data = [cell.get_text(strip=True) for cell in cells]

        game_date = GameDate(
            id=row_data[1].split('/')[1],
            domain=row_data[3].replace('.en.cx', '.encounter.cx'),
            start_date=row_data[4],
            name=row_data[5],
            author=re.sub(r'\s+', '', row_data[6]),
            price=row_data[7],
            game_type=game_type
        )

        games.append(game_date)

    parser_logger.info(f"Распарсено {len(games)} игр типа '{game_type}'.")
    return games


async def parse_additional_game_info(html: Optional[str]) -> AdditionalData:
    """
    Парсит дополнительные данные об игре.

    :param html: Текст HTML или None.
    :return: Объект AdditionalData.
    """
    additional_data = AdditionalData()

    if not html:
        return additional_data

    soup = BeautifulSoup(html, "html.parser")

    author_blocks = soup.find_all("span", id="lblFromAuthor")

    image = None

    # for block in author_blocks:
    #     next_tag = block.find_next()
    #     while next_tag:
    #         if next_tag.name == "img":
    #             image = next_tag["src"]
    #             break
    #         next_tag = next_tag.find_next()
    for img_tag in soup.find_all("img"):
        if any("обложка" in img_tag.get(attr, "").lower() for attr in ["title", "alt"]):
            image = img_tag["src"]
            break

    additional_data.image = image

    span_max_players = soup.find('span', id='spanMaxTeamPlayers')
    if span_max_players:
        additional_data.max_players = span_max_players.get_text(strip=True)

    end_date_td = soup.find_all('td', height="18")
    for span in end_date_td:
        if span and "Время окончания" in span.text:
            span_end_date = span.find('span', class_='white')
            if span_end_date:
                additional_data.end_date = ' '.join(span_end_date.text.strip().split()[:2])
                # print(f"Extracted end date text: {' '.join(span_end_date.text.strip().split()[:2])}")
                break

    return additional_data


async def fetch_and_parse_games(session: aiohttp.ClientSession, url: str, game_type: str) -> List[GameDate]:
    """
        Собирает и парсит данные игр с учетом пагинации.

        :param session: Объект aiohttp.ClientSession.
        :param url: URL игры.
        :param game_type: Тип игры (team или single).
        :return: Список объектов GameDate.
    """
    html = await fetch_html(session, url)
    if not html:
        parser_logger.warning(f"Не удалось загрузить страницу для URL: {url}")
        return []

    game_data = await parse_game_data(html, game_type=game_type)
    pagination_links = extract_pagination_links(html)

    for link in pagination_links:
        html = await fetch_html(session, link)
        data = await parse_game_data(html, game_type=game_type)
        game_data.extend(data)

    return game_data


async def gather_additional_game_data(session: aiohttp.ClientSession, game_data: List[GameDate]) -> None:
    """
    Собирает и добавляет дополнительные данные для каждой игры.

    :param session: Объект aiohttp.ClientSession.
    :param game_data: Список игр для обработки.
    """
    tasks = [fetch_html(session, game.link) for game in game_data]
    html_results = await asyncio.gather(*tasks)

    tasks_for_additional_data = []
    for game, html in zip(game_data, html_results):
        if html is None:
            parser_logger.warning(f"Не удалось загрузить HTML для игры ID={game.id}, ссылка: {game.link}")
        tasks_for_additional_data.append(parse_additional_game_info(html))

    additional_data_results = await asyncio.gather(*tasks_for_additional_data)

    for game, additional_data in zip(game_data, additional_data_results):
        game.max_players = extract_limit(additional_data.max_players)
        game.update_end_date(additional_data.end_date)
        game.image = additional_data.image


async def run_parsing() -> None:
    """
        Главная функция для запуска процесса парсинга.
    """
    max_connections = 150
    connector = aiohttp.TCPConnector(limit=max_connections, ssl=False)
    timeout = aiohttp.ClientTimeout(total=300)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        all_game_data = []
        for url, game_type in GAMES_URLS:
            game_data = await fetch_and_parse_games(session, url, game_type)
            all_game_data.extend(game_data)

        await gather_additional_game_data(session, all_game_data)

        parser_logger.info(f"Всего игр загружено: {len(all_game_data)}.")

        # existing_games = await game_dao.get_all()
        # existing_games = [game for game in existing_games if game.state != GameState.ACTIVE.value]
        # existing_game_ids = {game.id for game in existing_games}
        # parsed_game_ids = {game.id for game in all_game_data}
        #
        # games_to_delete = existing_game_ids - parsed_game_ids
        # if len(games_to_delete) < 9:
        #     for game_id in games_to_delete:
        #         await game_dao.delete(id=game_id)
        #         parser_logger.info(f"Удален объект: {game_id}")

        await asyncio.sleep(10)
        for game in all_game_data:
            await game_dao.create(**game.model_dump())

        parser_logger.info(f"Парсер завершил работу. Создано/обновлено записей: {len(all_game_data)}.")


async def parsing_active_games() -> None:
    active_games_from_db = {game.id for game in await game_dao.get_all(state=GameState.ACTIVE.value)}
    upcoming_games_from_db = {game.id for game in await game_dao.get_all(state=GameState.UPCOMING.value)}

    max_connections = 150
    connector = aiohttp.TCPConnector(limit=max_connections, ssl=False)
    timeout = aiohttp.ClientTimeout(total=300)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        active_game_data = []
        for url, game_type in ACTIVE_GAMES_URLS:
            game_data = await fetch_and_parse_games(session, url, game_type)
            if not game_data:
                # parser_logger.info("Получен пустой результат для игры из ACTIVE_GAMES_URLS. Откатываем изменения")
                parser_logger.info("Получен пустой результат для игры из ACTIVE_GAMES_URLS.")
                continue
            active_game_data.extend(game_data)

        await gather_additional_game_data(session, active_game_data)
        active_games_id = {game.id for game in active_game_data}
        if not active_games_id:
            parser_logger.info(
                f"Парсинг активных игр вернул 0 результатов. URL-список: {[u for u,_ in ACTIVE_GAMES_URLS]}"
            )
            return

        # Обновляем поля для игр, которые остаются активными
        still_active_games = active_games_from_db & active_games_id
        if still_active_games:
            parser_logger.info(f"Обновляем поля для {len(still_active_games)} активных игр")
            for game_id in still_active_games:
                game = next((g for g in active_game_data if g.id == game_id), None)
                if game:
                    await game_dao.create(**game.model_dump())
            parser_logger.info(f"Обновлено полей для {len(still_active_games)} активных игр")

        games_to_complete = active_games_from_db - active_games_id
        if len(games_to_complete) > 10:
            parser_logger.warning(f"⚠️ Подозрительно много игр для COMPLETED: {len(games_to_complete)}. Проверьте парсер!")
        if games_to_complete:
            parser_logger.info(f"Переводим в COMPLETED {len(games_to_complete)} игр: {games_to_complete}")
            async with game_dao.session_factory() as db_session:
                await db_session.execute(
                    update(GameModel)
                    .where(GameModel.id.in_(games_to_complete))
                    .values(state=GameState.COMPLETED.value)
                )
                parser_logger.info("Статусы игр успешно обновлены.")

                await db_session.execute(
                    delete(UserGameSubscription).where(UserGameSubscription.game_id.in_(games_to_complete))
                )
                await db_session.execute(
                    delete(UserGameRole).where(UserGameRole.game_id.in_(games_to_complete))
                )
                await db_session.commit()
        else:
            parser_logger.info("Все активные игры актуальны, обновление не требуется.")

        upcoming_games_data = []

        for url, game_type in GAMES_URLS:
            game_data = await fetch_and_parse_games(session, url, game_type)
            if not game_data:
                parser_logger.info("Получен пустой результат для игры из GAMES_URLS. Откатываем изменения")
                continue
            upcoming_games_data.extend(game_data)

        await gather_additional_game_data(session, upcoming_games_data)

        upcoming_games_id = {game.id for game in upcoming_games_data}
        if not upcoming_games_id:
            parser_logger.info(f"Парсинг не прошел. Кол-во предстоящих игр: {len(upcoming_games_id)}")
            return
        games_to_archive = []

        missing_upcoming_games = upcoming_games_from_db - upcoming_games_id
        if len(missing_upcoming_games) > 10:
            parser_logger.warning(f"⚠️ Подозрительно много игр для ACTIVE: {len(missing_upcoming_games)}. Проверьте парсер!")
        if missing_upcoming_games:
            for game_id in missing_upcoming_games:
                game = next((g for g in active_game_data if g.id == game_id), None)
                if game:
                    parser_logger.info(f"Обновляем игру {game_id}, переводим в ACTIVE и обновляем поля")
                    async with game_dao.session_factory() as db_session:
                        existing = await db_session.get(GameModel, game_id)
                        current_image_path = existing.image if existing else None

                        local_image = None
                        if game.image and isinstance(game.image, str) and game.image.startswith(("http://", "https://")):
                            local_image = await download_image(game_id=game.id, image_url=game.image)
                        image_to_store = local_image if local_image is not None else current_image_path

                        await db_session.execute(
                            update(GameModel)
                            .where(GameModel.id == game_id)
                            .values(name=game.name,
                                    start_date=game.start_date,
                                    end_date=game.end_date,
                                    image=image_to_store,
                                    image_url=game.image,
                                    state=GameState.ACTIVE.value)
                        )
                        await db_session.commit()
                        parser_logger.info(f"{game_id} обновлена")

                else:
                    games_to_archive.append(game_id)

        if len(games_to_archive) <= 5:
            for game_id in games_to_archive:
                parser_logger.info(f"Архивируем игру {game_id}")
                async with game_dao.session_factory() as db_session:
                    await db_session.execute(
                        update(GameModel)
                        .where(GameModel.id == game_id)
                        .values(state=GameState.ARCHIVED.value)
                    )
                    await db_session.commit()
            parser_logger.info(f"{games_to_archive} заархивированны.")

        if not games_to_archive:
            parser_logger.info("Все предстоящие игры актуальны, обновление не требуется.")

        parser_logger.info(
            f"Итог обновления активных/предстоящих игр: active_from_db={len(active_games_from_db)}, "
            f"active_parsed={len(active_games_id)}, completed={len(games_to_complete)}, "
            f"archived={len(games_to_archive)}, upcoming_from_db={len(upcoming_games_from_db)}, "
            f"upcoming_parsed={len(upcoming_games_id)}"
        )


if __name__ == "__main__":
    asyncio.run(run_parsing())

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from config import BOT_TOKEN, ADMIN_IDS
import database as db
from handlers import setup_routers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SOCKS5-прокси Happ (порт из настроек Happ)
PROXY_URL = "socks5://127.0.0.1:10808"


async def main():
    db.init_db()

    session = AiohttpSession(proxy=PROXY_URL)
    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(setup_routers())

    logger.info("Бот запущен. Админы: %s", ADMIN_IDS)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
import asyncio
from aiogram import Dispatcher
from app.handler.start import router as start
from app.handler.pair import router as pair
from app.handler.payment import router as payment
from app.handler.support import router as support
from app.handler.testing import router as testing
from app.handler.passport import router as passport
from core.config import bot

dp = Dispatcher()

async def main():
    dp.include_router(start)
    dp.include_router(pair)
    dp.include_router(payment)
    dp.include_router(support)
    dp.include_router(testing)
    dp.include_router(passport)

    # Запускаем consumer параллельно с polling
    await asyncio.gather(
        dp.start_polling(bot)
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")

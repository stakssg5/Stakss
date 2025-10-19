from __future__ import annotations

import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8000/")


async def on_start(message: types.Message) -> None:
    kb = InlineKeyboardBuilder()
    kb.button(text="Open Crypto PR+", web_app=types.WebAppInfo(url=WEBAPP_URL))
    await message.answer(
        "Welcome! Tap to open the mini app.",
        reply_markup=kb.as_markup(),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.message.register(on_start, CommandStart())
    return dp


async def run_bot() -> None:
    if not TELEGRAM_TOKEN:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN env var")
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = create_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_bot())

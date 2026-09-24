from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from bot.config import ADMIN_IDS
from bot.keyboards import main_menu

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer(
        "Привет! 👋\n\n"
        "Здесь ты можешь хранить лекции, видео-уроки и описания книг.\n"
        "Выбери действие в меню ниже.",
        reply_markup=main_menu(is_admin)
    )

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, or_
from bot.database import async_session
from bot.models import Category, Item
from bot.keyboards import categories_kb, items_kb, item_manage_kb
from bot.config import ADMIN_IDS
from bot.states import Search

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(F.text == "📚 Категории")
async def show_categories(message: Message):
    async with async_session() as session:
        result = await session.execute(select(Category).order_by(Category.name))
        categories = result.scalars().all()

    if not categories:
        await message.answer("Категорий пока нет.")
        return

    await message.answer("Выберите категорию:", reply_markup=categories_kb(categories))

@router.callback_query(F.data.startswith("cat_"))
async def show_items(callback: CallbackQuery):
    cat_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        result = await session.execute(
            select(Item).where(Item.category_id == cat_id).order_by(Item.title)
        )
        items = result.scalars().all()
        cat = await session.get(Category, cat_id)

    if not items:
        await callback.message.edit_text(f"В категории «{cat.name}» пока нет контента.")
        await callback.answer()
        return

    await callback.message.edit_text(
        f"Категория: <b>{cat.name}</b>\n\nВыберите материал:",
        reply_markup=items_kb(items),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("item_"))
async def show_item(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        item = await session.get(Item, item_id)
        if not item:
            await callback.answer("Не найдено", show_alert=True)
            return
        cat = await session.get(Category, item.category_id)

    type_names = {"lecture": "Лекция", "video": "Видео", "book": "Книга"}

    text = (
        f"<b>{item.title}</b>\n"
        f"Категория: {cat.name}\n"
        f"Тип: {type_names.get(item.content_type, item.content_type)}\n\n"
        f"{item.description or 'Без описания'}"
    )
    if item.media_url:
        text += f"\n\n🔗 <a href='{item.media_url}'>Ссылка</a>"

    markup = item_manage_kb(item.id) if is_admin(callback.from_user.id) else None

    if item.media_file_id:
        if item.content_type == "video":
            await callback.message.answer_video(item.media_file_id, caption=text, parse_mode="HTML", reply_markup=markup)
        else:
            await callback.message.answer_photo(item.media_file_id, caption=text, parse_mode="HTML", reply_markup=markup)
    else:
        await callback.message.answer(text, parse_mode="HTML", disable_web_page_preview=False, reply_markup=markup)

    await callback.answer()

@router.callback_query(F.data == "back_categories")
async def back_to_categories(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(select(Category).order_by(Category.name))
        categories = result.scalars().all()
    await callback.message.edit_text("Выберите категорию:", reply_markup=categories_kb(categories))
    await callback.answer()

@router.message(F.text == "🔍 Поиск")
async def search_start(message: Message, state: FSMContext):
    await message.answer("Введите ключевое слово для поиска:")
    await state.set_state(Search.query)

@router.message(Search.query)
async def process_search(message: Message, state: FSMContext):
    query = message.text.strip()
    async with async_session() as session:
        result = await session.execute(
            select(Item).where(
                or_(Item.title.ilike(f"%{query}%"), Item.description.ilike(f"%{query}%"))
            ).limit(30)
        )
        items = result.scalars().all()

    await state.clear()

    if not items:
        await message.answer("Ничего не найдено.")
        return

    text = f"🔍 Результаты поиска по запросу «{query}»:\n\n"
    for item in items:
        text += f"• <b>{item.title}</b>\n"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📁 Мои материалы")
async def my_materials(message: Message):
    if not is_admin(message.from_user.id):
        return

    async with async_session() as session:
        result = await session.execute(select(Item).order_by(Item.created_at.desc()).limit(50))
        items = result.scalars().all()

    if not items:
        await message.answer("У вас пока нет материалов.")
        return

    await message.answer(
        "Ваши материалы (последние 50):\nНажмите на материал, чтобы управлять им.",
        reply_markup=items_kb(items, show_manage=True)
    )

@router.callback_query(F.data == "back_my_materials")
async def back_my_materials(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(select(Item).order_by(Item.created_at.desc()).limit(50))
        items = result.scalars().all()
    await callback.message.edit_text(
        "Ваши материалы:",
        reply_markup=items_kb(items, show_manage=True)
    )
    await callback.answer()

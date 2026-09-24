from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from bot.config import ADMIN_IDS
from bot.database import async_session
from bot.models import Category, Item
from bot.keyboards import (
    admin_menu, main_menu, content_type_kb, skip_kb,
    categories_kb, confirm_delete_kb
)
from bot.states import AddCategory, AddItem, EditItem, DeleteCategory

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(F.text == "⚙️ Админ-панель")
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Админ-панель:", reply_markup=admin_menu())

@router.message(F.text == "◀️ Назад")
async def back_to_main(message: Message):
    await message.answer("Главное меню", reply_markup=main_menu(is_admin(message.from_user.id)))

# ===== ДОБАВИТЬ КАТЕГОРИЮ =====
@router.message(F.text == "➕ Добавить категорию")
async def add_category_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Введите название новой категории:")
    await state.set_state(AddCategory.name)

@router.message(AddCategory.name)
async def add_category_finish(message: Message, state: FSMContext):
    name = message.text.strip()
    async with async_session() as session:
        exists = await session.execute(select(Category).where(Category.name == name))
        if exists.scalar_one_or_none():
            await message.answer("Такая категория уже существует.")
            return
        session.add(Category(name=name))
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Категория «{name}» добавлена!", reply_markup=admin_menu())

# ===== УДАЛИТЬ КАТЕГОРИЮ =====
@router.message(F.text == "🗑 Удалить категорию")
async def delete_category_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    async with async_session() as session:
        result = await session.execute(select(Category).order_by(Category.name))
        categories = result.scalars().all()
    if not categories:
        await message.answer("Категорий нет.")
        return
    await message.answer(
        "Выберите категорию для удаления (вместе с ней удалится весь контент!):",
        reply_markup=categories_kb(categories, prefix="delcat")
    )
    await state.set_state(DeleteCategory.choose)

@router.callback_query(F.data.startswith("delcat_"))
async def delete_category_confirm(callback: CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        cat = await session.get(Category, cat_id)
        if not cat:
            await callback.answer("Категория не найдена", show_alert=True)
            return
        await callback.message.edit_text(
            f"Вы уверены, что хотите удалить категорию «{cat.name}» и весь её контент?",
            reply_markup=confirm_delete_kb(cat_id=cat_id)
        )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_del_cat_"))
async def delete_category_final(callback: CallbackQuery):
    cat_id = int(callback.data.split("_")[-1])
    async with async_session() as session:
        cat = await session.get(Category, cat_id)
        if cat:
            name = cat.name
            await session.delete(cat)
            await session.commit()
            await callback.message.edit_text(f"✅ Категория «{name}» удалена.")
        else:
            await callback.message.edit_text("Категория уже удалена.")
    await callback.answer()

@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    await callback.message.edit_text("Удаление отменено.")
    await callback.answer()

# ===== ДОБАВИТЬ КОНТЕНТ =====
@router.message(F.text == "➕ Добавить контент")
async def add_item_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    async with async_session() as session:
        result = await session.execute(select(Category).order_by(Category.name))
        categories = result.scalars().all()
    if not categories:
        await message.answer("Сначала создайте категорию.")
        return
    await message.answer("Выберите категорию:", reply_markup=categories_kb(categories))
    await state.set_state(AddItem.category)

@router.callback_query(AddItem.category, F.data.startswith("cat_"))
async def add_item_category(callback: CallbackQuery, state: FSMContext):
    await state.update_data(category_id=int(callback.data.split("_")[1]))
    await callback.message.edit_text("Введите название материала:")
    await state.set_state(AddItem.title)
    await callback.answer()

@router.message(AddItem.title)
async def add_item_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await message.answer("Введите описание (или «Пропустить»):", reply_markup=skip_kb())
    await state.set_state(AddItem.description)

@router.message(AddItem.description)
async def add_item_description(message: Message, state: FSMContext):
    desc = "" if message.text == "⏭ Пропустить" else message.text.strip()
    await state.update_data(description=desc)
    await message.answer("Выберите тип контента:", reply_markup=content_type_kb())
    await state.set_state(AddItem.content_type)

@router.callback_query(AddItem.content_type, F.data.startswith("type_"))
async def add_item_type(callback: CallbackQuery, state: FSMContext):
    await state.update_data(content_type=callback.data.split("_")[1])
    await callback.message.edit_text(
        "Отправьте фото / видео / любой файл (PDF, DOCX, ZIP и т.д.) или ссылку.\n"
        "Или нажмите «Пропустить».",
        reply_markup=None
    )
    await callback.message.answer("...", reply_markup=skip_kb())
    await state.set_state(AddItem.media)
    await callback.answer()

@router.message(AddItem.media)
async def add_item_media(message: Message, state: FSMContext):
    data = await state.get_data()
    media_file_id = None
    media_url = None
    content_type = data.get("content_type", "file")

    if message.text == "⏭ Пропустить":
        pass
    elif message.photo:
        media_file_id = message.photo[-1].file_id
        content_type = "photo"
    elif message.video:
        media_file_id = message.video.file_id
        content_type = "video"
    elif message.document:
        media_file_id = message.document.file_id
        content_type = "file"
    elif message.audio:
        media_file_id = message.audio.file_id
        content_type = "file"
    elif message.voice:
        media_file_id = message.voice.file_id
        content_type = "file"
    elif message.text and message.text.startswith("http"):
        media_url = message.text.strip()
    else:
        await message.answer(
            "Надішліть:\n"
            "• фото\n"
            "• відео\n"
            "• будь-який файл (PDF, DOCX, ZIP тощо)\n"
            "• або посилання\n\n"
            "Або натисніть «Пропустить»."
        )
        return

    async with async_session() as session:
        session.add(Item(
            category_id=data["category_id"],
            title=data["title"],
            description=data.get("description", ""),
            content_type=content_type,
            media_file_id=media_file_id,
            media_url=media_url
        ))
        await session.commit()

    await state.clear()
    await message.answer("✅ Контент добавлен!", reply_markup=admin_menu())

# ===== УДАЛЕНИЕ КОНТЕНТА =====
@router.callback_query(F.data.startswith("del_item_"))
async def delete_item_confirm(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[-1])
    async with async_session() as session:
        item = await session.get(Item, item_id)
        if not item:
            await callback.answer("Уже удалено", show_alert=True)
            return
        await callback.message.edit_text(
            f"Удалить материал «{item.title}»?",
            reply_markup=confirm_delete_kb(item_id=item_id)
        )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_del_item_"))
async def delete_item_final(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[-1])
    async with async_session() as session:
        item = await session.get(Item, item_id)
        if item:
            title = item.title
            await session.delete(item)
            await session.commit()
            await callback.message.edit_text(f"✅ Материал «{title}» удалён.")
        else:
            await callback.message.edit_text("Материал уже удалён.")
    await callback.answer()

# ===== РЕДАКТИРОВАНИЕ =====
@router.callback_query(F.data.startswith("edit_"))
async def edit_item_start(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        item = await session.get(Item, item_id)
        if not item:
            await callback.answer("Не найдено", show_alert=True)
            return
        await state.update_data(item_id=item_id)
        await callback.message.edit_text(
            f"Редактирование: <b>{item.title}</b>\n\n"
            f"Отправьте новое название (или нажмите «Пропустить»):",
            parse_mode="HTML"
        )
        await callback.message.answer("...", reply_markup=skip_kb())
    await state.set_state(EditItem.title)
    await callback.answer()

@router.message(EditItem.title)
async def edit_item_title(message: Message, state: FSMContext):
    if message.text != "⏭ Пропустить":
        await state.update_data(title=message.text.strip())
    await message.answer("Новое описание (или «Пропустить»):", reply_markup=skip_kb())
    await state.set_state(EditItem.description)

@router.message(EditItem.description)
async def edit_item_description(message: Message, state: FSMContext):
    if message.text != "⏭ Пропустить":
        await state.update_data(description=message.text.strip())
    await message.answer("Выберите новый тип (или пропустите):", reply_markup=content_type_kb())
    await state.set_state(EditItem.content_type)

@router.callback_query(EditItem.content_type, F.data.startswith("type_"))
async def edit_item_type(callback: CallbackQuery, state: FSMContext):
    await state.update_data(content_type=callback.data.split("_")[1])
    await callback.message.edit_text(
        "Отправьте новое фото / видео / любой файл или ссылку.\nИли нажмите «Пропустить»:",
        reply_markup=None
    )
    await callback.message.answer("...", reply_markup=skip_kb())
    await state.set_state(EditItem.media)
    await callback.answer()

@router.message(EditItem.media)
async def edit_item_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    item_id = data["item_id"]

    async with async_session() as session:
        item = await session.get(Item, item_id)
        if not item:
            await message.answer("Материал не найден.")
            await state.clear()
            return

        if "title" in data:
            item.title = data["title"]
        if "description" in data:
            item.description = data["description"]
        if "content_type" in data:
            item.content_type = data["content_type"]

        if message.text == "⏭ Пропустить":
            pass
        elif message.photo:
            item.media_file_id = message.photo[-1].file_id
            item.media_url = None
            item.content_type = "photo"
        elif message.video:
            item.media_file_id = message.video.file_id
            item.media_url = None
            item.content_type = "video"
        elif message.document:
            item.media_file_id = message.document.file_id
            item.media_url = None
            item.content_type = "file"
        elif message.audio:
            item.media_file_id = message.audio.file_id
            item.media_url = None
            item.content_type = "file"
        elif message.voice:
            item.media_file_id = message.voice.file_id
            item.media_url = None
            item.content_type = "file"
        elif message.text and message.text.startswith("http"):
            item.media_url = message.text.strip()
            item.media_file_id = None

        await session.commit()

    await state.clear()
    await message.answer("✅ Материал обновлён!", reply_markup=admin_menu())

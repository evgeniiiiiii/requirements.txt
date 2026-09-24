from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu(is_admin: bool = False):
    kb = [
        [KeyboardButton(text="📚 Категории")],
        [KeyboardButton(text="🔍 Поиск")],
    ]
    if is_admin:
        kb.append([KeyboardButton(text="📁 Мои материалы")])
        kb.append([KeyboardButton(text="⚙️ Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить категорию")],
            [KeyboardButton(text="➕ Добавить контент")],
            [KeyboardButton(text="🗑 Удалить категорию")],
            [KeyboardButton(text="◀️ Назад")],
        ],
        resize_keyboard=True
    )

def categories_kb(categories, prefix="cat"):
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat.name, callback_data=f"{prefix}_{cat.id}")
    builder.adjust(1)
    return builder.as_markup()

def items_kb(items, show_manage: bool = False):
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(text=item.title, callback_data=f"item_{item.id}")
    if show_manage:
        builder.button(text="◀️ Назад", callback_data="back_my_materials")
    else:
        builder.button(text="◀️ Назад к категориям", callback_data="back_categories")
    builder.adjust(1)
    return builder.as_markup()

def content_type_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 Лекция", callback_data="type_lecture")
    builder.button(text="🎬 Видео", callback_data="type_video")
    builder.button(text="📚 Книга", callback_data="type_book")
    builder.adjust(1)
    return builder.as_markup()

def skip_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⏭ Пропустить")]],
        resize_keyboard=True
    )

def item_manage_kb(item_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать", callback_data=f"edit_{item_id}")
    builder.button(text="🗑 Удалить", callback_data=f"del_item_{item_id}")
    builder.button(text="◀️ Назад", callback_data="back_my_materials")
    builder.adjust(1)
    return builder.as_markup()

def confirm_delete_kb(item_id: int = None, cat_id: int = None):
    builder = InlineKeyboardBuilder()
    if item_id:
        builder.button(text="✅ Да, удалить", callback_data=f"confirm_del_item_{item_id}")
    if cat_id:
        builder.button(text="✅ Да, удалить", callback_data=f"confirm_del_cat_{cat_id}")
    builder.button(text="❌ Отмена", callback_data="cancel_delete")
    builder.adjust(1)
    return builder.as_markup()

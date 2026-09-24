from aiogram.fsm.state import State, StatesGroup

class AddCategory(StatesGroup):
    name = State()

class AddItem(StatesGroup):
    category = State()
    title = State()
    description = State()
    content_type = State()
    media = State()

class EditItem(StatesGroup):
    title = State()
    description = State()
    content_type = State()
    media = State()

class Search(StatesGroup):
    query = State()

class DeleteCategory(StatesGroup):
    choose = State()

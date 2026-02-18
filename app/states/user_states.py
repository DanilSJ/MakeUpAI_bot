from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    # Основные состояния
    new = State()
    paid = State()
    waiting_partner = State()
    testing = State()
    generating = State()
    completed = State()
    support_menu = State()
    # Дополнительные состояния
    waiting_invite_code = State()
    answering_question = State()
    ai_translator = State()


class TestStates(StatesGroup):
    # Состояния для тестирования (7 блоков)
    block1 = State()
    block2 = State()
    block3 = State()
    block4 = State()
    block5 = State()
    block6 = State()
    block7 = State()
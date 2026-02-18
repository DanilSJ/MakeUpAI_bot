from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# Главное меню для новых пользователей
def get_start_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔘 Начать тестирование"))
    builder.add(KeyboardButton(text="🔘 Как это работает?"))
    builder.add(KeyboardButton(text="🔘 У меня есть код приглашения"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

# Меню после оплаты (тестирование не завершено)
def get_testing_menu_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔘 Продолжить тест"))
    builder.add(KeyboardButton(text="🔘 Статус пары"))
    builder.add(KeyboardButton(text="🔘 Поддержка"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

# Меню во время генерации
def get_generating_menu_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔘 Проверить статус"))
    builder.add(KeyboardButton(text="🔘 Вернуться в меню"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

# Меню готового паспорта
def get_passport_menu_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔘 Скачать Паспорт"))
    builder.add(KeyboardButton(text="🔘 AI-Переводчик"))
    builder.add(KeyboardButton(text="🔘 Что дальше?"))
    builder.add(KeyboardButton(text="🔘 Поддержка"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

# Клавиатура для пары
def get_pair_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔘 Скопировать код"))
    builder.add(KeyboardButton(text="🔘 Проверить, присоединился ли партнёр"))
    builder.add(KeyboardButton(text="🔘 Вернуться в меню"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

# Клавиатура для AI-переводчика
def get_ai_translator_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔘 Задать ещё вопрос"))
    builder.add(KeyboardButton(text="🔘 Вернуться к Паспорту"))
    builder.add(KeyboardButton(text="🔘 Выйти в меню"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

# Клавиатура поддержки
def get_support_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔘 Написать администратору"))
    builder.add(KeyboardButton(text="🔘 Частые вопросы"))
    builder.add(KeyboardButton(text="🔘 Вернуться назад"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

# Инлайн кнопка для возврата
def get_back_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="◀️ Вернуться назад", callback_data="back"))
    return builder.as_markup()
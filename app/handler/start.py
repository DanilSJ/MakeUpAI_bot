from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.api.utils import api
from app.handler.payment import start_testing
from app.keyboards.reply import get_start_keyboard, get_back_inline_keyboard, get_testing_menu_keyboard
from app.states.user_states import UserStates

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    # Создаем пользователя в БД
    user = await api.create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username
    )

    # Устанавливаем состояние
    await state.set_state(UserStates.new)

    # Отправляем приветствие
    welcome_text = (
        "🔍 *Это инженерный анализ совместимости двух личностей.*\n\n"
        "Вы получите Паспорт ДНК ваших отношений.\n\n"
        "Выберите действие:"
    )

    await message.answer(
        welcome_text,
        reply_markup=get_start_keyboard(),
        parse_mode="Markdown"
    )


@router.message(F.text == "🔘 Как это работает?")
async def how_it_works(message: Message, state: FSMContext):
    info_text = (
        "📋 *Что такое Паспорт ДНК*\n"
        "Это уникальный анализ совместимости двух личностей.\n\n"
        "📊 *Что входит в анализ*\n"
        "• Психологический профиль\n"
        "• Совместимость характеров\n"
        "• Рекомендации по отношениям\n\n"
        "⏱ *Сколько времени займёт*\n"
        "Тестирование состоит из 7 блоков, примерно 15-20 минут.\n\n"
        "🔒 *Конфиденциальность*\n"
        "Все данные защищены и не передаются третьим лицам."
    )

    await message.answer(
        info_text,
        reply_markup=get_back_inline_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "back")
async def go_back(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()

    if current_state in [UserStates.waiting_invite_code, UserStates.paid]:
        await callback.message.edit_text(
            "Выберите действие:",
            reply_markup=None
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_start_keyboard()
        )

    await callback.answer()


@router.message(F.text == "🔘 У меня есть код приглашения")
async def invite_code_input(message: Message, state: FSMContext):
    await state.set_state(UserStates.waiting_invite_code)
    await message.answer(
        "Введите ваш код приглашения:",
        reply_markup=get_back_inline_keyboard()
    )


@router.message(UserStates.waiting_invite_code)
async def process_invite_code(message: Message, state: FSMContext):
    if message.text == "🔘 Начать тестирование":
        return await start_testing(message, state)

    invite_code = message.text.strip()

    try:
        # Получаем информацию о паре по коду
        pair_info = await api.get_pair_by_invite_code(invite_code)

        if pair_info.get("error"):
            if "Pier does not exist" in pair_info.get("message", ""):
                await message.answer("❌ Пара с таким кодом не найдена. Попробуйте снова:")
            else:
                await message.answer(f"❌ Ошибка при поиске пары: {pair_info.get('message')}")
            return

        # Проверяем, что пользователь не владелец своей же пары
        if pair_info.get("user_owner_telegram_id") == message.from_user.id:
            await message.answer("❌ Вы не можете присоединиться к своей собственной паре.")
            return

        # Присоединяемся к паре
        pair = await api.join_pair(
            telegram_id=message.from_user.id,
            invite_code=invite_code
        )

        # Проверяем, есть ли ошибка при join
        if pair.get("error"):
            await message.answer(f"❌ Ошибка при присоединении: {pair.get('message')}")
            return

        # Если все прошло успешно
        await state.set_state(UserStates.paid)
        await state.update_data(invite_code=invite_code)
        await message.answer(
            "✅ Вы успешно присоединились к паре!\n\n"
            "Теперь вы можете начать тестирование.",
            reply_markup=get_testing_menu_keyboard()
        )

    except Exception as e:
        # На случай неожиданных ошибок
        await message.answer("❌ Произошла ошибка при присоединении к паре. Попробуйте позже.")

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from app.api.utils import api
from app.keyboards.reply import get_pair_keyboard, get_testing_menu_keyboard
from app.states.user_states import UserStates

router = Router()


@router.message(F.text == "🔘 Скопировать код")
async def copy_code(message: Message, state: FSMContext):
    # Получаем информацию о паре
    pair = await api.get_user_active_pair(message.from_user.id)
    if not pair:
        await message.answer("❌ Пара не найдена")
        return

    await message.answer(
        f"🔑 Ваш код приглашения:\n`{pair['invite_code']}`\n\n"
        "Отправьте его партнёру.",
        parse_mode="Markdown"
    )


@router.message(F.text == "🔘 Проверить, присоединился ли партнёр")
async def check_partner(message: Message, state: FSMContext):

    # Получаем данные из FSM
    data = await state.get_data()
    invite_code = data.get("invite_code")

    if not invite_code:
        await message.answer("❌ Код приглашения не найден.")
        return

    # Получаем пару по invite_code
    pair = await api.get_pair_by_invite_code(invite_code)

    # Проверка ошибки API
    if not pair or pair.get("error"):
        await message.answer("❌ Ошибка при получении данных пары.")
        return

    # Проверяем присоединился ли партнёр
    if pair.get("user_pair_telegram_id"):
        await state.set_state(UserStates.testing)
        await state.update_data(invite_code=invite_code)
        await message.answer(
            "🎉 *Партнёр присоединился!*\n\n"
            "Теперь вы можете начать тестирование.",
            reply_markup=get_testing_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await state.set_state(UserStates.waiting_partner)

        await message.answer(
            "⏳ Партнёр ещё не присоединился.\n"
            "Ожидаем второго участника..."
        )

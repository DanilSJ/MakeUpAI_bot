from aiogram import Router, F
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice
from aiogram.fsm.context import FSMContext

from app.api.utils import api
from core.config import settings
from app.keyboards.reply import get_back_inline_keyboard
from app.states.user_states import UserStates

router = Router()

PRICE = 1  # рублей



@router.message(F.text == "🔘 Начать тестирование")
async def start_testing(message: Message, state: FSMContext):
    # Получаем информацию о пользователе из базы
    user = await api.get_user(message.from_user.id)

    if not user or user.get("error"):
        await message.answer("❌ Не удалось получить данные пользователя.")
        return

    # Если есть подписка basic или тестовый режим
    subscription = user.get("subscription")
    if subscription == "basic" or settings.TEST_MODE:
        await grant_access(message, state)
        return

    # Иначе показываем экран оплаты
    await message.answer(
        "💳 *Полный анализ для пары — 8 900 ₽*\n\n"
        "После оплаты вы получите доступ к тестированию.",
        parse_mode="Markdown"
    )

    await message.answer_invoice(
        title="Паспорт ДНК отношений",
        description="Полный анализ совместимости для пары",
        payload="passport_payment",
        currency="XTR",  # 🔥 ВАЖНО
        prices=[LabeledPrice(label="Пара", amount=1)],  # ✅ Используем LabeledPrice
    )


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext):
    await api.upgrade_to_basic_subscription(message.from_user.id)

    await grant_access(message, state)


async def grant_access(message: Message, state: FSMContext):
    # Устанавливаем статус пользователя как оплаченный
    await api.update_user_status(
        telegram_id=message.from_user.id,
        status="paid"
    )
    await state.set_state(UserStates.paid)

    pair = await api.create_pair(
        telegram_id=message.from_user.id,
        status="waiting"
    )

    if not pair or pair.get("error"):
        await message.answer("❌ Ошибка при создании пары.")
        return

    invite_code = pair.get("invite_code")
    if not invite_code:
        await message.answer("❌ Invite code не получен.")
        return

    await state.update_data(invite_code=invite_code)

    await message.answer(
        "✅ *Доступ предоставлен!*\n\n"
        f"📱 *Отправьте этот код партнёру:*\n"
        f"`{invite_code}`\n\n"
        "Партнёр должен ввести его в разделе «У меня есть код приглашения»",
        parse_mode="Markdown"
    )

    from app.keyboards.reply import get_pair_keyboard
    await message.answer(
        "Ожидаем второго участника...",
        reply_markup=get_pair_keyboard()
    )
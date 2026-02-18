from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from app.keyboards.reply import get_support_keyboard, get_back_inline_keyboard
from app.states.user_states import UserStates
from core.config import settings

router = Router()


@router.message(F.text == "🔘 Поддержка")
async def support_menu(message: Message, state: FSMContext):
    await state.set_state(UserStates.support_menu)
    await message.answer(
        "🆘 *Поддержка*\n\n"
        "Выберите вариант:",
        reply_markup=get_support_keyboard(),
        parse_mode="Markdown"
    )


@router.message(F.text == "🔘 Написать администратору")
async def contact_admin(message: Message):
    # Перенаправляем сообщение администратору
    admin_id = settings.ADMIN_ID  # Добавьте в .env

    await message.answer(
        "📨 Ваше сообщение отправлено администратору.\n"
        "Ожидайте ответа в ближайшее время."
    )

    # Отправляем уведомление администратору
    await message.bot.send_message(
        admin_id,
        f"Новое сообщение от @{message.from_user.username}:\n\n{message.text}"
    )


@router.message(F.text == "🔘 Частые вопросы")
async def faq(message: Message):
    faq_text = (
        "❓ *Часто задаваемые вопросы*\n\n"
        "**Q: Сколько времени занимает тест?**\n"
        "A: Около 15-20 минут.\n\n"
        "**Q: Когда будет готов паспорт?**\n"
        "A: После прохождения всех 7 блоков обоими партнёрами.\n\n"
        "**Q: Можно ли пройти тест заново?**\n"
        "A: Да, обратитесь в поддержку.\n\n"
        "**Q: Как пригласить партнёра?**\n"
        "A: После оплаты вы получите код приглашения."
    )

    await message.answer(faq_text, parse_mode="Markdown")
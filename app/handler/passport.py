from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from app.ai.utils import ai
from app.api.utils import api
from app.keyboards.reply import get_passport_menu_keyboard, get_ai_translator_keyboard
from app.states.user_states import UserStates
from fpdf import FPDF, HTMLMixin
from io import BytesIO

router = Router()

# Счетчик вопросов AI
ai_questions_count = {}
SAFE_MAX_QUESTIONS = 20

class PDF(FPDF, HTMLMixin):
    pass


async def generate_passport_pdf(passport_html: str) -> BytesIO:
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # 🔥 Подключаем Unicode-шрифты
    pdf.add_font(
        family="DejaVu",
        style="",
        fname="font/DejaVuSansCondensed.ttf",
        uni=True
    )
    pdf.add_font(
        family="DejaVu",
        style="B",
        fname="font/DejaVuSansCondensed-Bold.ttf",
        uni=True
    )
    pdf.add_font(
        family="DejaVu",
        style="I",
        fname="font/DejaVuSansCondensed-Oblique.ttf",
        uni=True
    )

    pdf.set_font("DejaVu", size=11)

    # FPDF лучше воспринимает <br> чем \n
    passport_html = passport_html.replace("\n", "<br>")

    pdf.write_html(passport_html)

    # Новая версия fpdf2 возвращает bytearray
    pdf_bytes = pdf.output(dest="S")

    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)

    return buffer


@router.message(F.text == "🔘 Скачать Паспорт")
async def download_passport(message: Message, state: FSMContext):
    """Отправка паспорта безопасно: краткий HTML + PDF"""
    data = await state.get_data()

    invite_code = data.get("invite_code")
    pair = await api.get_pair_by_invite_code(invite_code)
    pair_id = pair["id"]

    if not pair_id:
        pair = await api.get_user_active_pair(message.from_user.id)
        if not pair:
            await message.answer("❌ Пара не найдена")
            return
        pair_id = pair["id"]
        await state.update_data(pair_id=pair_id)

    # Получаем/генерируем паспорт
    passport_result = data.get("passport")

    # Если паспорта нет в состоянии - генерируем новый
    if not passport_result:
        # Генерируем профиль, если нужно
        profile_result = await api.generate_profile(pair_id)
        if not profile_result or profile_result.get("error"):
            await message.answer("❌ Профиль ещё не готов. Подождите и попробуйте позже.")
            return

        # Генерируем паспорт
        passport_result = await api.generate_passport(pair_id)

        # Проверяем результат генерации паспорта
        if not passport_result:
            await message.answer("❌ Паспорт пока недоступен. API вернул пустой ответ.")
            return

        if passport_result.get("error"):
            await message.answer(f"❌ Ошибка API: {passport_result.get('error')}")
            return

        # Сохраняем в состояние
        await state.update_data(passport=passport_result)

    # ИЗВЛЕКАЕМ КОНТЕНТ ИЗ ПАСПОРТА
    passport_content = None

    # Проверяем структуру ответа
    if isinstance(passport_result, dict):
        # Вариант 1: passport_result содержит поле passport с content
        if "passport" in passport_result and isinstance(passport_result["passport"], dict):
            passport_content = passport_result["passport"].get("content")

        # Вариант 2: прямой content в passport_result
        elif "content" in passport_result:
            passport_content = passport_result["content"]

    if not passport_content:
        await message.answer(
            "❌ Паспорт пока недоступен или имеет неверный формат.\n"
            "Если вы только что завершили тест — подождите и нажмите «Проверить статус»."
        )
        print(f"DEBUG - passport_result: {passport_result}")
        return

    # 1️⃣ Отправляем текст в HTML формате с безопасным разбиением
    SAFE_CHUNK_SIZE = 3500  # Консервативный размер с запасом

    # Добавляем заголовок, если его нет в контенте
    if not passport_content.startswith("<b>📋 ПАСПОРТ ПАРЫ</b>"):
        full_content = "<b>📋 ПАСПОРТ ПАРЫ</b>\n\n" + passport_content
    else:
        full_content = passport_content

    # Разбиваем на части по границам абзацев
    paragraphs = full_content.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # Проверяем, поместится ли абзац в текущий чанк
        if len(current_chunk) + len(para) + 2 > SAFE_CHUNK_SIZE:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

    # Добавляем последний чанк
    if current_chunk:
        chunks.append(current_chunk)

    # Отправляем все чанки
    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            # Добавляем навигацию по частям
            if i == 0:
                chunk_with_nav = f"{chunk}\n\n<i>📄 Часть 1/{len(chunks)}</i>"
            elif i == len(chunks) - 1:
                chunk_with_nav = f"{chunk}\n\n<i>📄 Часть {i + 1}/{len(chunks)} (окончание)</i>"
            else:
                chunk_with_nav = f"{chunk}\n\n<i>📄 Часть {i + 1}/{len(chunks)}</i>"

            await message.answer(chunk_with_nav, parse_mode="HTML")
        else:
            await message.answer(chunk, parse_mode="HTML")

    # 2️⃣ Генерируем PDF из контента
    try:
        pdf_buffer = await generate_passport_pdf(passport_content)

        pdf_buffer.seek(0)
        pdf_file = BufferedInputFile(pdf_buffer.read(), filename=f"passport_pair_{pair_id}.pdf")

        await message.answer_document(
            pdf_file,
            caption="✅ Ваш Паспорт в PDF формате"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при генерации PDF: {escape_html(str(e))}")


def escape_html(text: str) -> str:
    """
    Экранирует специальные символы HTML для безопасного отображения.
    """
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&apos;",
        ">": "&gt;",
        "<": "&lt;",
    }
    return "".join(html_escape_table.get(c, c) for c in text)
@router.message(F.text.in_(["🔘 AI-Переводчик", "🔘 Задать ещё вопрос"]))



@router.message(F.text.in_(["🔘 AI-Переводчик", "🔘 Задать ещё вопрос"]))
async def ai_translator(message: Message, state: FSMContext):
    """
    Начало сессии AI-переводчика
    """
    await state.set_state(UserStates.ai_translator)
    user_id = message.from_user.id
    ai_questions_count[user_id] = SAFE_MAX_QUESTIONS  # инициализация

    await message.answer(
        "🤖 <b>AI-Переводчик</b>\n\n"
        "Опишите ситуацию или конфликт, и я помогу вам перевести «язык травмы» на «язык любви».\n\n"
        f"Доступно вопросов: {SAFE_MAX_QUESTIONS}/{SAFE_MAX_QUESTIONS}",
        reply_markup=get_ai_translator_keyboard(),
        parse_mode="HTML"
    )

@router.message(UserStates.ai_translator, F.text)
async def process_ai_question(message: Message, state: FSMContext):
    user_text = message.text.strip()
    user_id = message.from_user.id

    # Игнорируем системные команды
    ignored_commands = [
        "🔘 Вернуться к Паспорту",
        "🔘 AI-Переводчик",
        "🔘 Задать ещё вопрос"
    ]
    if user_text in ignored_commands:
        return

    # Инициализация локального счётчика
    question_count = ai_questions_count.get(user_id, SAFE_MAX_QUESTIONS)

    if question_count <= 0:
        await message.answer(
            "❌ Вы исчерпали лимит вопросов (20).\n"
            "Через 5 часов пополним лимит"
        )
        return

    # Системное описание для AI
    system_prompt = (
        "Ты эксперт по отношениям. Твоя цель — переводить «язык травмы» на «язык любви» "
        "коротко и понятно, чтобы партнёры понимали истинные чувства друг друга.\n"
        "Примеры:\n"
        "Партнер А говорит: «Мне нужно побыть одному» → «У меня сенсорная перегрузка. "
        "Я ухожу в док-станцию на перезарядку, чтобы вернуться к тебе полным сил»\n"
        "Партнер Б говорит: «Нам нужно серьезно поговорить прямо сейчас» → «Я чувствую потерю связи и тревогу. "
        "Мне нужно подтверждение, что мы все еще вместе»\n"
        "Ответ должен быть кратким (не более 3-4 предложений), дружелюбным и без лишней воды."
    )

    # Обращение к AI
    try:
        ai_response = await ai.deepseek(prompt=user_text, system_prompt=system_prompt)
        ai_response = escape_html(ai_response)
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при обращении к AI: {escape_html(str(e))}")
        return

    # Уменьшаем счётчик локально и на сервере
    question_count -= 1
    ai_questions_count[user_id] = question_count
    await api.update_ai_questions(user_id, question_count)

    # Если вопросы закончились, устанавливаем время восстановления
    if question_count == 0:
        await api.set_ai_recharge_time(user_id, hours=5)

    # Отправляем ответ пользователю
    await message.answer(
        f"🤖 <b>Перевод с «языка травмы» на «язык любви»:</b>\n\n{ai_response}\n\n"
        f"Осталось вопросов: {question_count}/{SAFE_MAX_QUESTIONS}",
        parse_mode="HTML"
    )

@router.message(F.text == "🔘 Вернуться к Паспорту")
async def back_to_passport(message: Message, state: FSMContext):
    await state.set_state(UserStates.completed)
    await message.answer(
        "📄 <b>Меню Паспорта:</b>",
        reply_markup=get_passport_menu_keyboard(),
        parse_mode="HTML"
    )

@router.message(UserStates.ai_translator, F.text)
async def process_ai_question(message: Message, state: FSMContext):
    user_text = message.text.strip()

    # Игнорируем системные команды
    ignored_commands = [
        "🔘 Вернуться к Паспорту",
        "🔘 AI-Переводчик",
        "🔘 Задать ещё вопрос"
    ]
    if user_text in ignored_commands:
        return  # просто не обрабатываем, команды имеют свои хэндлеры

    user_id = message.from_user.id
    question_count = ai_questions_count.get(user_id, 0)

    if question_count >= 20:
        await message.answer(
            "❌ Вы исчерпали лимит вопросов (20).\n"
            "Через 5 часов лимит пополнится"
        )
        return

    # Системное описание для AI
    system_prompt = (
        "Ты эксперт по отношениям. Твоя цель — переводить «язык травмы» на «язык любви» "
        "коротко и понятно, чтобы партнёры понимали истинные чувства друг друга.\n"
        "Примеры:\n"
        "Партнер А говорит: «Мне нужно побыть одному» → «У меня сенсорная перегрузка. "
        "Я ухожу в док-станцию на перезарядку, чтобы вернуться к тебе полным сил»\n"
        "Партнер Б говорит: «Нам нужно серьезно поговорить прямо сейчас» → «Я чувствую потерю связи и тревогу. "
        "Мне нужно подтверждение, что мы все еще вместе»\n"
        "Ответ должен быть кратким (не более 3-4 предложений), дружелюбным и без лишней воды."
    )

    try:
        ai_response = await ai.deepseek(prompt=user_text, system_prompt=system_prompt)
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при обращении к AI: {e}")
        return

    await message.answer(
        f"🤖 *Перевод с «языка травмы» на «язык любви»:*\n\n{ai_response}\n\n"
        f"Осталось вопросов: {20 - question_count - 1}/20",
        parse_mode="Markdown"
    )

    ai_questions_count[user_id] = question_count + 1


@router.message(F.text == "🔘 Вернуться к Паспорту")
async def back_to_passport(message: Message, state: FSMContext):
    await state.set_state(UserStates.completed)
    await message.answer(
        "📄 *Меню Паспорта:*",
        reply_markup=get_passport_menu_keyboard(),
        parse_mode="Markdown"
    )

def sanitize_text_for_markdown(text: str) -> str:
    """
    Убирает/заменяет символы, которые ломают Markdown.
    """
    # Telegram не любит эти символы: _*[]()~`>#+-=|{}.!
    forbidden_chars = r"_*[]()~`>#+-=|{}.!\""
    sanitized = "".join(c if c not in forbidden_chars else "" for c in text)
    return sanitized

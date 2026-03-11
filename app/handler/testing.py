from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.types import InputFile
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from app.api.utils import api, logger
from app.keyboards.reply import get_back_inline_keyboard, get_testing_menu_keyboard, get_start_keyboard, \
    get_passport_menu_keyboard
from app.states.user_states import TestStates, UserStates

router = Router()
SYSTEM_BUTTONS = [
    "🔘 Прервать и продолжить позже",
    "🔘 Написать текстом",
    # "🔘 Ответить голосом"
]
# Тестовые вопросы (7 блоков)
QUESTIONS = [
    {
        "text": "Блок 1: Как вы реагируете на стресс?\n\n"
                "Вспомните последнюю сложную или стрессовую ситуацию вне отношений.\n"
                "Как вы себя вели и чего подсознательно ждали от партнера в этот момент?",
        "hint": "Опишите конкретную ситуацию."
    },
    {
        "text": "Блок 2: Что для вас важнее всего?\n\n"
                "Без чего ваши отношения потеряли бы для вас всякий смысл?\n"
                "А что дало бы вам больше всего радости, сил и ощущения ценности отношений?",
        "hint": "Попробуйте описать ключевые ценности."
    },
    {
        "text": "Блок 3: Как вы выражаете любовь?\n\n"
                "Опишите идеальную жизнь с партнером, когда вы чувствуете максимальную близость.\n"
                "Что вы при этом делаете?",
        "hint": "Какие действия создают ощущение любви?"
    },
    {
        "text": "Блок 4: Как вы решаете конфликты?\n\n"
                "Вы сильно не согласны с партнером по важному вопросу.\n"
                "Ваша первая реакция:\n"
                "доказать свою правоту, промолчать, уйти или что-то другое?\n\n"
                "Опишите механику вашей реакции.",
        "hint": "Что происходит в первые минуты конфликта?"
    },
    {
        "text": "Блок 5: Что вас привлекает в партнере?\n\n"
                "Какая черта характера или привычка партнера восхищает вас больше всего?",
        "hint": "Это может быть поведение, ценность или привычка."
    },
    {
        "text": "Блок 6: Как вы проводите свободное время?\n\n"
                "У вас есть полностью свободный день.\n"
                "Как вы проведете его вместе?",
        "hint": "Опишите идеальный сценарий."
    },
    {
        "text": "Блок 7: Тест на системную когерентность\n\n"
                "Представьте: у вас есть красная кнопка.\n"
                "Если нажать её — из партнера исчезнет черта, которая вас больше всего раздражает.\n\n"
                "Но вместе с ней исчезнет и та черта, которая восхищает вас больше всего.\n"
                "(они связаны одним алгоритмом).\n\n"
                "Вы нажмете кнопку?\n"
                "Почему да или почему нет?",
        "hint": "Ответ показывает глубинное принятие личности партнера."
    }
]

CONTEXT_QUESTION = {
    "text": "🔹 Нулевой шаг — Контекст ваших отношений\n\n"
            "1️⃣ Ваш текущий статус?\n"
            "(Встречаемся / Живем вместе / В браке / На грани разрыва)\n\n"
            "2️⃣ Опишите ваши отношения в нескольких словах.\n"
            "Какие вызовы стоят перед вами?\n"
            "Что получается лучше всего?\n"
            "Какие есть проблемы?",
    "hint": "Ответ можно написать свободным текстом."
}

# Маппинг состояний на индексы вопросов
STATE_TO_INDEX = {
    TestStates.block1: 0,
    TestStates.block2: 1,
    TestStates.block3: 2,
    TestStates.block4: 3,
    TestStates.block5: 4,
    TestStates.block6: 5,
    TestStates.block7: 6,
}

# Маппинг индексов на состояния
INDEX_TO_STATE = {
    0: TestStates.block1,
    1: TestStates.block2,
    2: TestStates.block3,
    3: TestStates.block4,
    4: TestStates.block5,
    5: TestStates.block6,
    6: TestStates.block7,
}

def get_upgrade_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Перейти на уровень: Полный Паспорт",
                    url="https://onomichi.io/resonance"
                )
            ]
        ]
    )
    return keyboard

@router.message(F.text == "🔘 Продолжить тест")
async def continue_test(message: Message, state: FSMContext):
    """Продолжение теста или запуск с нулевого шага (контекст отношений)"""

    data = await state.get_data()
    invite_code = data.get("invite_code")

    pair = await api.get_pair_by_invite_code(invite_code)

    if not pair:
        await message.answer(
            "❌ Ошибка: пара не найдена.\nСоздайте или присоединитесь к паре."
        )
        return

    pair_id = pair["id"]

    await state.update_data(pair_id=pair_id)

    # Проверяем сохраненное состояние
    paused_state = data.get("paused_state")
    current_question = data.get("current_question", 0)

    if paused_state:
        await state.set_state(paused_state)

        await message.answer(
            f"⏯ Продолжаем тест\n"
            f"Вопрос {current_question + 1}/{len(QUESTIONS)}",
            parse_mode="Markdown"
        )

        await send_question(message, state, current_question)
        return

    # Если тест новый — начинаем с НУЛЕВОГО ШАГА
    await state.set_state(TestStates.context)

    await state.update_data(
        answers={},
        current_question=0
    )

    context_text = (
        "🔹 *Нулевой шаг — Контекст ваших отношений*\n\n"
        "1️⃣ Ваш текущий статус?\n"
        "• Встречаемся\n"
        "• Живем вместе\n"
        "• В браке\n"
        "• На грани разрыва\n\n"
        "2️⃣ Опишите ваши отношения в нескольких словах:\n"
        "• Какие вызовы стоят перед вами?\n"
        "• Что получается лучше всего?\n"
        "• Какие есть проблемы?\n\n"
        "✍️ Напишите ответ одним сообщением."
    )

    await message.answer(
        context_text,
        parse_mode="Markdown"
    )

    # Создаем тестовую сессию первого блока заранее
    start_result = await api.start_test(
        telegram_id=message.from_user.id,
        pair_id=pair_id,
        block=0  # контекстный блок
    )

    if start_result and start_result.get("error"):
        logger.warning(
            f"Could not create context test session: {start_result}"
        )

@router.message(TestStates.context, F.text)
async def process_context(message: Message, state: FSMContext):

    await state.update_data(context=message.text)

    await state.set_state(TestStates.block1)

    await state.update_data(
        answers={},
        current_question=0
    )

    await send_question(message, state, 0)

async def send_question(message: Message, state: FSMContext, question_index: int):
    """Отправляет вопрос пользователю"""
    question = QUESTIONS[question_index]

    # Обновляем текущий вопрос в данных
    await state.update_data(current_question=question_index)

    text = (
        f"{question['text']}\n\n"
        f"💡 *Подсказка:* {question['hint']}\n\n"
        "Выберите способ ответа:"
    )

    # Создаем клавиатуру с вариантами ответа
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            # [KeyboardButton(text="🔘 Ответить голосом")],
            [KeyboardButton(text="🔘 Написать текстом")],
            [KeyboardButton(text="🔘 Прервать и продолжить позже")]
        ],
        resize_keyboard=True
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(F.text == "🔘 Написать текстом")
async def text_answer(message: Message, state: FSMContext):
    """Пользователь выбрал ответ текстом"""
    await message.answer("📝 Напишите ваш ответ:")


@router.message(F.text == "🔘 Ответить голосом")
async def voice_answer(message: Message, state: FSMContext):
    """Пользователь выбрал ответ голосом"""
    await message.answer("🎤 Отправьте голосовое сообщение с вашим ответом:")

@router.message(F.text == "🔘 Прервать и продолжить позже")
async def pause_test(message: Message, state: FSMContext):
    """Прерывание теста"""
    # Сохраняем текущее состояние
    current_state = await state.get_state()
    data = await state.get_data()

    # Обновляем статус пользователя
    await state.set_state(UserStates.testing)

    # Сохраняем, что тест прерван на определенном вопросе
    await state.update_data(paused_state=current_state)

    await message.answer(
        "⏸ *Тест прерван*\n\n"
        "Вы можете продолжить позже, нажав «Продолжить тест».\n"
        f"Прогресс сохранён: вопрос {data.get('current_question', 0) + 1}/{len(QUESTIONS)}",
        reply_markup=get_testing_menu_keyboard(),
        parse_mode="Markdown"
    )


@router.message(TestStates.block1, F.text)
@router.message(TestStates.block2, F.text)
@router.message(TestStates.block3, F.text)
@router.message(TestStates.block4, F.text)
@router.message(TestStates.block5, F.text)
@router.message(TestStates.block6, F.text)
@router.message(TestStates.block7, F.text)
async def process_text_answer(message: Message, state: FSMContext):
    """Обработка текстового ответа"""
    if message.text in SYSTEM_BUTTONS:
        return  # ничего не делаем, чтобы хендлер не срабатывал

    current_state = await state.get_state()

    # Получаем текущий индекс вопроса из состояния
    question_index = STATE_TO_INDEX.get(current_state)

    if question_index is None:
        await message.answer("Произошла ошибка. Начните тест заново.")
        await state.clear()
        return

    # Получаем данные
    data = await state.get_data()
    pair_id = data.get('pair_id')

    if not pair_id:
        # Если нет pair_id, получаем из API
        pair = await api.get_user_active_pair(message.from_user.id)
        if pair:
            pair_id = pair["id"]
            await state.update_data(pair_id=pair_id)
        else:
            await message.answer("Ошибка: пара не найдена")
            return

    # Получаем вопрос для текущего блока
    question_text = QUESTIONS[question_index]["text"]

    # Сохраняем ответ в state (для истории)
    data = await state.get_data()
    answers = data.get('answers', {})
    answers[question_index] = {
        'question': question_text,
        'answer': message.text
    }
    await state.update_data(answers=answers)

    # Сохраняем ответ и получаем insight
    context = data.get("context")

    result = await api.save_answer_and_get_insight(
        telegram_id=message.from_user.id,
        pair_id=pair_id,
        block=question_index + 1,
        answer=message.text,
        context=context
    )

    # Показываем insight от AI
    if result.get("insight"):
        insight_text = result["insight"]
        if isinstance(insight_text, dict):
            insight_text = insight_text.get("text", str(insight_text))

        await message.answer(
            f"✨ *Мини-инсайт:*\n{insight_text}",
            parse_mode="Markdown"
        )

    # Проверяем, был ли это последний вопрос
    if question_index == len(QUESTIONS) - 1:
        # Тест завершен - отмечаем в API и завершаем
        await finish_test(message, state, answers)
    else:
        # Переходим к следующему вопросу
        next_index = question_index + 1
        next_state = INDEX_TO_STATE[next_index]

        # Создаем тестовую сессию для следующего блока
        next_block = next_index + 1  # блоки с 1
        start_result = await api.start_test(
            telegram_id=message.from_user.id,
            pair_id=pair_id,
            block=next_block
        )
        if start_result and start_result.get("error"):
            logger.warning(f"Could not start test session for block {next_block}: {start_result}")

        # Устанавливаем следующее состояние
        await state.set_state(next_state)

        # Отправляем следующий вопрос
        await send_question(message, state, next_index)

        # Показываем прогресс
        await message.answer(
            f"📊 Вы прошли {next_index} из {len(QUESTIONS)} блоков.\n"
            f"Осталось: {len(QUESTIONS) - next_index}",
            parse_mode="Markdown"
        )


async def finish_test(message: Message, state: FSMContext, answers: dict):
    """Завершение теста"""
    try:
        data = await state.get_data()
        invite_code = data.get("invite_code")
        pair = await api.get_pair_by_invite_code(invite_code)
        pair_id = pair["id"]

        if not pair_id:
            # Пробуем получить пару из API
            pair = await api.get_user_active_pair(message.from_user.id)
            if pair:
                pair_id = pair["id"]
                await state.update_data(pair_id=pair_id)
            else:
                await message.answer("❌ Ошибка: пара не найдена")
                return

        # Отмечаем в API, что пользователь завершил тест
        mark_result = await api.mark_user_test_completed(pair_id, message.from_user.id)
        if mark_result and mark_result.get("error"):
            logger.error(f"Failed to mark test completed: {mark_result}")

        # Проверяем, завершили ли оба пользователя тест
        both_completed_check = await api.check_both_tests_completed(pair_id)

        await api.analyze_block(pair["id"], message.from_user.id)

        if both_completed_check.get("both_completed"):
            # Оба завершили - запускаем генерацию
            await state.set_state(UserStates.generating)

            from app.keyboards.reply import get_generating_menu_keyboard
            await message.answer(
                "🔄 *Анализируем архитектуру личности…*\n\n"
                "Это займёт несколько минут.\n"
                "Нажмите «Проверить статус», чтобы получить Паспорт.",
                reply_markup=get_generating_menu_keyboard(),
                parse_mode="Markdown"
            )

            # Запускаем генерацию
            await api.analyze_block(pair_id, message.from_user.id)

            profile_result = await api.generate_profile(pair_id)
            if profile_result and not profile_result.get("error"):
                passport_result = await api.generate_passport(pair_id)

                if passport_result and not passport_result.get("error") and passport_result.get("passport"):
                    await state.update_data(passport=passport_result)
                    await state.set_state(UserStates.completed)

                    # Отправляем пользователю паспорт текстом и PDF
                    await send_passport(message, state, passport_result.get("passport"))
                else:
                    # Профиль готов, паспорт ещё нет
                    await state.update_data(profile=profile_result)
            else:
                # Профиль генерируется
                pass
        else:
            # Ждем второго партнера
            await state.set_state(UserStates.testing)

            # Определяем, кто ещё не завершил
            waiting_for = ""
            if not both_completed_check.get("owner_completed"):
                waiting_for = "владельца пары"
            elif not both_completed_check.get("pair_completed"):
                waiting_for = "партнёра"

            await message.answer(
                f"✅ *Вы завершили тест!*\n\n"
                f"⏳ Ожидаем, когда {waiting_for} завершит тестирование.\n\n"
                "Вы можете периодически проверять «Статус пары».",
                parse_mode="Markdown"
            )

            from app.keyboards.reply import get_testing_menu_keyboard
            await message.answer("Меню:", reply_markup=get_testing_menu_keyboard())

    except Exception as e:
        logger.error(f"Error in finish_test: {e}")
        await message.answer(
            "❌ Произошла ошибка при завершении теста.\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку."
        )


@router.message(F.text == "🔘 Статус пары")
async def check_pair_status(message: Message, state: FSMContext):
    """Проверка статуса пары и запуск генерации при готовности"""
    data = await state.get_data()
    invite_code = data.get("invite_code")

    pair = await api.get_pair_by_invite_code(invite_code)

    if not pair:
        await message.answer("❌ Пара не найдена")
        return

    # Получаем актуальный статус пары через API
    pair_info = await api.get_pair(pair["id"])

    if not pair_info:
        await message.answer("❌ Не удалось получить информацию о паре")
        return

    # Формируем текст статуса
    status_text = f"📊 *Статус пары*\n\n"
    status_text += f"🆔 ID пары: {pair_info.get('id', 'N/A')}\n\n"

    # Статус владельца
    owner_status = "✅ Завершил тест" if pair_info.get('user_owner_complete_test') else "⏳ Проходит тест"
    status_text += f"👤 Владелец: {owner_status}\n"

    # Статус партнёра
    if pair_info.get('user_pair_telegram_id'):
        pair_status = "✅ Завершил тест" if pair_info.get('user_pair_complete_test') else "⏳ Проходит тест"
        status_text += f"👤 Партнёр: {pair_status}\n"
    else:
        status_text += f"👤 Партнёр: ⏳ Ожидание присоединения\n"

    # Проверяем готовность к генерации
    user_owner_complete = pair_info.get('user_owner_complete_test', False)
    user_pair_complete = pair_info.get('user_pair_complete_test', False)

    if user_owner_complete and user_pair_complete:
        # Проверяем, не запущена ли уже генерация
        if not pair_info.get('profile_complete') and not pair_info.get('passport_complete'):
            # Запускаем генерацию
            status_text += "\n✨ *Оба готовы!* Запускаем генерацию паспорта..."

            # Получаем данные из state или создаем новый state
            current_state = await state.get_state()
            data = await state.get_data()

            # Устанавливаем состояние generating, если ещё не в нём
            if current_state != UserStates.generating:
                await state.set_state(UserStates.generating)

                from app.keyboards.reply import get_generating_menu_keyboard
                await message.answer(
                    "🔄 *Анализируем архитектуру личности…*\n\n"
                    "Это займёт несколько минут.\n"
                    "Нажмите «Проверить статус», чтобы получить Паспорт.",
                    reply_markup=get_generating_menu_keyboard(),
                    parse_mode="Markdown"
                )

            # Запускаем генерацию в фоне
            await api.analyze_block(pair["id"], message.from_user.id)

            # Генерируем профиль
            profile_result = await api.generate_profile(pair["id"])
            if profile_result and not profile_result.get("error"):
                await state.update_data(profile=profile_result)

                # Генерируем паспорт
                passport_result = await api.generate_passport(pair["id"])
                if passport_result and not passport_result.get("error") and passport_result.get("passport"):
                    await state.update_data(passport=passport_result)
                    await state.set_state(UserStates.completed)

                    # Не отправляем сообщение здесь, так как пользователь уже в процессе
                    # Проверим статус позже через кнопку "Проверить статус"

            # Получаем обновленную информацию о паре после генерации
            pair_info = await api.get_pair(pair["id"])

        # Проверяем статус генерации после возможного запуска
        if pair_info.get('profile_complete'):
            status_text += "\n📊 Профиль: ✅ Сгенерирован"
        if pair_info.get('passport_complete'):
            status_text += "\n📄 Паспорт: ✅ Готов"
            # Если паспорт готов, предлагаем скачать
            if pair_info.get('passport_complete'):
                from app.keyboards.reply import get_passport_menu_keyboard
                await message.answer(
                    "✅ *Паспорт готов!*\n\n"
                    "Нажмите «Скачать Паспорт».",
                    reply_markup=get_passport_menu_keyboard(),
                    parse_mode="Markdown"
                )
                # Не отправляем статус, так как уже отправили сообщение о готовности
                return
    elif user_owner_complete or user_pair_complete:
        status_text += "\n⏳ Один из партнёров завершил тест, ожидаем второго..."

    await message.answer(status_text, parse_mode="Markdown")

@router.message(F.text == "🔘 Проверить статус")
async def check_generation_status(message: Message, state: FSMContext):
    """Проверка статуса генерации"""
    data = await state.get_data()
    pair_id = data.get("pair_id")

    if not pair_id:
        pair = await api.get_user_active_pair(message.from_user.id)
        if not pair:
            await message.answer("❌ Пара не найдена")
            return
        pair_id = pair["id"]
        await state.update_data(pair_id=pair_id)

    # Получаем актуальную информацию о паре
    pair_info = await api.get_pair(pair_id)
    if not pair_info:
        await message.answer("❌ Не удалось получить информацию о паре")
        return

    # Проверяем, готовы ли оба пользователя
    user_owner_complete = pair_info.get('user_owner_complete_test', False)
    user_pair_complete = pair_info.get('user_pair_complete_test', False)

    if not (user_owner_complete and user_pair_complete):
        await message.answer(
            "⏳ Ожидаем завершения тестирования обоими партнёрами.\n"
            "Проверьте статус пары."
        )
        return

    # Проверяем статус генерации
    if pair_info.get('passport_complete'):
        # Паспорт уже готов
        passport_result = {"passport": True}  # Здесь нужно получить реальный паспорт
        await state.update_data(passport=passport_result)
        await state.set_state(UserStates.completed)

        from app.keyboards.reply import get_passport_menu_keyboard
        await message.answer(
            "✅ *Паспорт готов!*\n\n"
            "Нажмите «Скачать Паспорт».",
            reply_markup=get_passport_menu_keyboard(),
            parse_mode="Markdown"
        )
        return

    # Проверяем статус генерации профиля
    if not pair_info.get('profile_complete'):
        profile_result = await api.generate_profile(pair_id)
        if not profile_result or profile_result.get("error"):
            await message.answer(
                "🔄 Профиль ещё генерируется...\n"
                "Пожалуйста, подождите и нажмите «Проверить статус» позже."
            )
            return
        await state.update_data(profile=profile_result)

    # Профиль готов, проверяем/генерируем паспорт
    passport_result = await api.generate_passport(pair_id)
    if passport_result and not passport_result.get("error") and passport_result.get("passport"):
        await state.update_data(passport=passport_result)
        await state.set_state(UserStates.completed)

        # Отправляем пользователю паспорт текстом и PDF
        await send_passport(message, state, passport_result.get("passport"))

    else:
        await message.answer(
            "🔄 Паспорт ещё генерируется...\n"
            "Пожалуйста, подождите и нажмите «Проверить статус» позже."
        )


@router.message(F.text == "🔘 Вернуться в меню")
async def back_to_menu(message: Message, state: FSMContext):
    """Возврат в главное меню продукта"""
    await state.set_state(UserStates.testing)
    await message.answer("Меню:", reply_markup=get_testing_menu_keyboard())

@router.message(F.text == "🔘 Вернуться назад")
async def go_back(message: Message, state: FSMContext):
    current_state = await state.get_state()

    # Пример логики: если мы в поддержке, возвращаемся к паспортному меню
    if current_state == UserStates.support_menu:
        await message.answer(
            "📄 Меню Паспорта:",
            reply_markup=get_passport_menu_keyboard()
        )
    else:
        # По умолчанию — главное меню
        await message.answer(
            "🏠 Главное меню:",
            reply_markup=get_start_keyboard()
        )

async def send_passport(message: Message, state: FSMContext, passport_data: dict):
    """Отправка паспорта текстом и PDF"""
    # Формируем текстовую версию
    passport_text = "📄 *Ваш Паспорт личности*\n\n"
    for key, value in passport_data.items():
        passport_text += f"*{key}:* {value}\n"

    await message.answer(passport_text, parse_mode="Markdown")

    # Генерация PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Заголовок
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height - 50, "Паспорт личности")

    # Содержание
    c.setFont("Helvetica", 14)
    y = height - 100
    for key, value in passport_data.items():
        text_line = f"{key}: {value}"
        c.drawString(50, y, text_line)
        y -= 25
        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 14)
            y = height - 50

    c.save()
    buffer.seek(0)

    # Отправка PDF
    pdf_file = InputFile(buffer, filename="passport.pdf")
    await message.answer_document(
        pdf_file,
        caption="✅ Ваш Паспорт в PDF формате",
        parse_mode="Markdown"
    )

    # Paywall CTA
    upgrade_text = (
        "📊 *Базовый анализ завершен.*\n\n"
        "Мы выявили ваши зоны резонанса, но также обнаружили "
        "структурные противоречия, которые могут привести к "
        "критическому трению в будущем.\n\n"
        "Бесплатный анализ показывает *ЧТО происходит.*\n\n"
        "*Полный Паспорт Отношений и AI-Медиатор покажут — КАК ЭТО ИСПРАВИТЬ.*"
    )

    await message.answer(
        upgrade_text,
        reply_markup=get_upgrade_keyboard(),
        parse_mode="Markdown"
    )
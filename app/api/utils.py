from core.config import settings
from httpx import AsyncClient, HTTPError
from typing import Optional, Dict, Any, List
import json
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class API:
    def __init__(self):
        self.url_api = settings.URL_API
        self.timeout = 20.0

    async def _make_request(self, method: str, endpoint: str, **kwargs):
        """Универсальный метод для запросов с обработкой ошибок"""
        url = f"{self.url_api}{endpoint}"
        async with AsyncClient(timeout=self.timeout) as client:
            try:
                logger.info(f"Making {method} request to {url}")
                logger.info(f"Kwargs: {kwargs}")

                response = await client.request(method, url, **kwargs)

                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response content: {response.text[:200]}")  # Первые 200 символов

                if response.status_code == 200:
                    if response.content:
                        return response.json()
                    else:
                        logger.warning(f"Empty response from {url}")
                        return {}
                else:
                    logger.error(f"Error response {response.status_code}: {response.text}")
                    return {
                        "error": True,
                        "status_code": response.status_code,
                        "message": response.text
                    }
            except HTTPError as e:
                logger.error(f"HTTP error: {e}")
                return {"error": True, "message": str(e)}
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                return {"error": True, "message": f"Invalid JSON response: {e}"}
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return {"error": True, "message": str(e)}

    # ========== USERS ==========

    async def create_user(self, telegram_id: int, username: str = None, status: str = "new"):
        """Создание нового пользователя"""
        return await self._make_request(
            "POST",
            "/users/",
            json={
                "telegram_id": telegram_id,
                "username": username,
                "status": status,
            }
        )

    async def get_user(self, telegram_id: int):
        """Получение пользователя по telegram_id"""
        return await self._make_request(
            "GET",
            f"/users/{telegram_id}/",
            params={"telegram_id": telegram_id}
        )

    async def update_user_status(self, telegram_id: int, status: str):
        """Обновление статуса пользователя"""
        return await self._make_request(
            "PATCH",
            f"/users/{telegram_id}/update",
            params={"telegram_id": telegram_id},
            json={"status": status}
        )

    # ========== PAIRS ==========

    async def create_pair(self, telegram_id: int, status: str = "waiting"):
        """Создание пары"""
        return await self._make_request(
            "POST",
            "/pairs/create/",
            json={
                "user_owner_telegram_id": telegram_id,
                "status": status,
            }
        )

    async def join_pair(self, telegram_id: int, invite_code: str):
        """Присоединение к паре по коду"""
        return await self._make_request(
            "POST",
            "/pairs/join/",
            json={
                "user_pair_telegram_id": telegram_id,
                "invite_code": invite_code,
            }
        )

    async def get_pair(self, pair_id: int):
        """Получение пары по ID"""
        result = await self._make_request(
            "GET",  # В вашем API это POST
            f"/pairs/{pair_id}/",
        )

        # Если получили ошибку или пустой ответ, возвращаем None
        if isinstance(result, dict) and result.get("error"):
            logger.error(f"Error getting pair {pair_id}: {result}")
            return None
        return result

    async def get_pair_by_user(self, telegram_id: int):
        """Получение пары по telegram_id пользователя"""
        return await self._make_request(
            "GET",
            f"/pairs/by-user/{telegram_id}/",
        )

    async def get_pair_by_invite_code(self, invite_code: str):
        """Получечние пары по коду приглашения"""
        return await self._make_request(
            "GET",
            f"/pairs/by-invite/{invite_code}/",
        )

    async def update_pair_status(self, pair_id: int, status: str):
        """Обновление статуса пары"""
        return await self._make_request(
            "POST",
            f"/pairs/{pair_id}/status/",
            json={"status": status}
        )

    # ========== НОВЫЕ МЕТОДЫ ДЛЯ ОБНОВЛЕНИЯ СТАТУСА ТЕСТА ==========

    async def update_owner_test_status(self, pair_id: int, test_complete: bool = True):
        """
        Обновление статуса завершения теста для владельца пары
        PATCH /pairs/{pair_id}/owner-test/?test_complete=true
        """
        return await self._make_request(
            "PATCH",
            f"/pairs/{pair_id}/owner-test/",
            params={"test_complete": str(test_complete).lower()}
        )

    async def update_pair_test_status(self, pair_id: int, test_complete: bool = True):
        """
        Обновление статуса завершения теста для партнёра пары
        PATCH /pairs/{pair_id}/pair-test/?test_complete=true
        """
        return await self._make_request(
            "PATCH",
            f"/pairs/{pair_id}/pair-test/",
            params={"test_complete": str(test_complete).lower()}
        )

    async def mark_user_test_completed(self, pair_id: int, telegram_id: int) -> Dict:
        """
        Отметить, что пользователь завершил тест.
        Автоматически определяет, является ли пользователь владельцем или партнёром
        и обновляет соответствующий статус.
        """
        try:
            # Получаем информацию о паре
            pair = await self.get_pair(pair_id)
            if not pair:
                return {"error": True, "message": "Пара не найдена"}

            # Определяем роль пользователя
            if pair.get("user_owner_telegram_id") == telegram_id:
                # Пользователь - владелец
                result = await self.update_owner_test_status(pair_id, True)
                logger.info(f"Marked owner test completed for pair {pair_id}")
                return result
            elif pair.get("user_pair_telegram_id") == telegram_id:
                # Пользователь - партнёр
                result = await self.update_pair_test_status(pair_id, True)
                logger.info(f"Marked pair test completed for pair {pair_id}")
                return result
            else:
                return {"error": True, "message": "Пользователь не найден в паре"}

        except Exception as e:
            logger.error(f"Error marking test completed: {e}")
            return {"error": True, "message": str(e)}

    async def check_both_tests_completed(self, pair_id: int) -> Dict:
        """
        Проверить, завершили ли оба пользователя тест
        Возвращает статус и информацию о готовности
        """
        try:
            pair = await self.get_pair(pair_id)
            if not pair:
                return {
                    "both_completed": False,
                    "error": True,
                    "message": "Пара не найдена"
                }

            user_owner_complete = pair.get("user_owner_complete_test", False)
            user_pair_complete = pair.get("user_pair_complete_test", False)

            return {
                "both_completed": user_owner_complete and user_pair_complete,
                "owner_completed": user_owner_complete,
                "pair_completed": user_pair_complete,
                "pair": pair
            }

        except Exception as e:
            logger.error(f"Error checking tests completed: {e}")
            return {
                "both_completed": False,
                "error": True,
                "message": str(e)
            }

    # ========== TEST ==========

    async def start_test(self, telegram_id: int, pair_id: int, block: int = 1):
        """Начало теста для пользователя"""
        return await self._make_request(
            "POST",
            "/test/start/",
            json={
                "telegram_id": telegram_id,
                "pair_id": pair_id,
                "block": block,
            }
        )

    async def submit_test(self, payload: dict):
        """
        Отправка ответов на сервер.
        Ожидается payload в формате:
        {
            "telegram_id": ...,
            "pair_id": ...,
            "questions": "текст вопроса",
            "answer": "текущий ответ",
            "current_block": ...,
            "total_blocks": ...,
            "success": true/false
        }
        """
        return await self._make_request(
            "POST",
            "/test/submit/",
            json=payload
        )

    # ========== AI ==========

    async def analyze_block(self, pair_id: int, telegram_id: int):
        """Анализ ответов блока"""
        return await self._make_request(
            "POST",
            "/ai/analyze/",
            params={
                "pair_id": pair_id,
                "telegram_id": telegram_id
            }
        )

    async def generate_profile(self, pair_id: int):
        """Генерация профилей пользователей"""
        return await self._make_request(
            "POST",
            "/ai/profile/",
            params={"pair_id": pair_id}
        )

    async def generate_passport(self, pair_id: int):
        """Генерация паспорта пары"""
        return await self._make_request(
            "POST",
            f"/ai/passport/{pair_id}/",
        )

    # ========== ЛОГИКА ТЕСТИРОВАНИЯ ==========

    async def save_answer_and_get_insight(self, telegram_id: int, pair_id: int,
                                          block: int, answer: str):
        """
        Сохранить ответ на блок и получить insight от AI.
        Сначала создает тестовую сессию (если нужно), затем отправляет ответ.
        """
        try:
            # Получаем вопрос из списка QUESTIONS
            from app.handler.testing import QUESTIONS  # Импортируем список вопросов

            # Получаем текст вопроса для текущего блока
            question_text = QUESTIONS[block - 1]["text"] if block <= len(QUESTIONS) else "Вопрос не найден"

            # Создаем тестовую сессию для текущего блока (если еще не создана)
            try:
                await self.start_test(telegram_id, pair_id, block)
            except Exception as e:
                logger.debug(f"Test session may already exist for block {block}: {e}")

            # Формируем payload в формате, который ожидает API
            payload = {
                "telegram_id": telegram_id,
                "pair_id": pair_id,
                "questions": question_text,
                "answer": answer,
                "current_block": block,
                "total_blocks": len(QUESTIONS),
                "success": True
            }

            # Отправляем на сервер
            result = await self.submit_test(payload)

            # Получаем insight из ответа
            insight = None
            if result and not result.get("error"):
                insight = result.get("insight")

            # Если это последний блок (block == 7), отмечаем тест как завершенный
            if block == len(QUESTIONS):
                await self.mark_user_test_completed(pair_id, telegram_id)
                logger.info(f"User {telegram_id} completed all tests for pair {pair_id}")

            return {
                "insight": insight,
                "error": result.get("error") if isinstance(result, dict) else False
            }

        except Exception as e:
            logger.error(f"Error in save_answer_and_get_insight: {e}")
            return {
                "insight": None,
                "error": True,
                "error_message": str(e)
            }

    async def get_user_answers(self, telegram_id: int, pair_id: int) -> Dict:
        """
        Получить ответы пользователя.
        """
        # API не предоставляет endpoint для получения ответов
        return {}

    async def is_test_completed(self, telegram_id: int, pair_id: int) -> bool:
        """
        Проверить, завершил ли пользователь тест.
        Использует поля user_owner_complete_test и user_pair_complete_test
        """
        try:
            pair = await self.get_pair(pair_id)
            if not pair:
                return False

            if pair.get("user_owner_telegram_id") == telegram_id:
                return pair.get("user_owner_complete_test", False)
            elif pair.get("user_pair_telegram_id") == telegram_id:
                return pair.get("user_pair_complete_test", False)
            else:
                return False

        except Exception as e:
            logger.error(f"Error checking test completion: {e}")
            return False

    async def get_pair_test_status(self, pair_id: int) -> Dict:
        """
        Получить статус тестирования пары
        """
        try:
            pair = await self.get_pair(pair_id)

            # Проверяем, что получили пару
            if not pair or (isinstance(pair, dict) and pair.get("error")):
                logger.error(f"Pair not found or error: {pair}")
                return {
                    "status": "error",
                    "message": "Пара не найдена",
                    "user1_completed": False,
                    "user2_completed": False
                }

            user1_completed = pair.get("user_owner_complete_test", False)
            user2_completed = pair.get("user_pair_complete_test", False) if pair.get("user_pair_telegram_id") else False

            # Определяем статус
            if not pair.get("user_pair_telegram_id"):
                status = "waiting_partner"
                message = "⏳ Ожидаем второго участника"
            elif user1_completed and user2_completed:
                status = "ready"
                message = "✅ Оба партнёра завершили тест! Генерируем паспорт..."
            elif user1_completed or user2_completed:
                status = "partial"
                message = "⏳ Один из партнёров ещё проходит тест"
            else:
                status = "testing"
                message = "📝 Оба партнёра проходят тестирование"

            return {
                "status": status,
                "user1_completed": user1_completed,
                "user2_completed": user2_completed,
                "message": message,
                "pair": pair
            }
        except Exception as e:
            logger.error(f"Error in get_pair_test_status: {e}")
            return {
                "status": "error",
                "message": f"Ошибка проверки статуса: {str(e)}",
                "user1_completed": False,
                "user2_completed": False
            }

    async def check_and_update_pair_status(self, pair_id: int) -> Dict:
        """
        Проверить статус пары и обновить его если нужно
        """
        try:
            status_info = await self.get_pair_test_status(pair_id)

            if status_info["status"] == "error":
                return status_info

            # Обновляем статус в БД если изменился
            current_status = status_info["status"]

            status_mapping = {
                "waiting_partner": "waiting",
                "partial": "partial",
                "ready": "ready",
                "testing": "testing"
            }

            db_status = status_mapping.get(current_status, "waiting")
            await self.update_pair_status(pair_id, db_status)

            # Если оба готовы, запускаем генерацию профиля, затем паспорта
            if current_status == "ready":
                # Сначала генерируем профиль
                profile = await self.generate_profile(pair_id)
                status_info["profile"] = profile

                # Если профиль успешно сгенерирован, генерируем паспорт
                if profile and not profile.get("error"):
                    passport = await self.generate_passport(pair_id)
                    status_info["passport"] = passport

            return status_info
        except Exception as e:
            logger.error(f"Error in check_and_update_pair_status: {e}")
            return {
                "status": "error",
                "message": f"Ошибка обновления статуса: {str(e)}"
            }

    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========

    async def get_or_create_user(self, telegram_id: int, username: str = None):
        """Получить или создать пользователя"""
        try:
            user = await self.get_user(telegram_id)
            if user and not user.get("error") and "id" in user:
                return user
        except:
            pass

        return await self.create_user(telegram_id, username)

    async def get_user_active_pair(self, telegram_id: int):
        """Получить активную пару пользователя"""
        try:
            pair = await self.get_pair_by_user(telegram_id)
            if pair and not pair.get("error"):
                return pair
            return None
        except Exception as e:
            logger.error(f"Error getting user active pair: {e}")
            return None

    async def update_ai_questions(self, telegram_id: int, remaining: int):
        """
        PATCH /users/{telegram_id}/ai-question
        Обновляем количество оставшихся AI-вопросов
        """
        return await self._make_request(
            "PATCH",
            f"/users/{telegram_id}/ai-question",
            headers={"accept": "application/json", "Content-Type": "application/json"},
            json={"ai_question": remaining}
        )

    async def set_ai_recharge_time(self, telegram_id: int, hours: int = 3):
        """
        PATCH /users/{telegram_id}/ai-recharge-time
        Устанавливаем время восстановления AI-вопросов на сервере (+3 часов по умолчанию)
        """
        new_time = (datetime.utcnow() + timedelta(hours=hours)).isoformat() + "Z"
        return await self._make_request(
            "PATCH",
            f"/users/{telegram_id}/ai-recharge-time",
            headers={"accept": "application/json", "Content-Type": "application/json"},
            json={"ai_recharge_time": new_time}
        )

    async def upgrade_to_basic_subscription(self, telegram_id: int, days: int = 30):
        """
        Обновить подписку пользователя на basic и установить subscription_end +days дней от текущей даты.
        """
        try:
            subscription_end = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"
            return await self._make_request(
                "PATCH",
                f"/users/{telegram_id}/subscription",
                headers={"accept": "application/json", "Content-Type": "application/json"},
                json={
                    "subscription": "basic",
                    "subscription_end": subscription_end
                }
            )
        except Exception as e:
            logger.error(f"Error upgrading subscription for {telegram_id}: {e}")
            return {"error": True, "message": str(e)}

api = API()
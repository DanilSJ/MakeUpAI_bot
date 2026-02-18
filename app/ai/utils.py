from httpx import AsyncClient, ReadTimeout, HTTPStatusError
from core.config import settings


class AI:
    def __init__(self):
        self.token = settings.TOKEN_AI
        self.headers = {"Authorization": self.token}
        self.url_ai = settings.URL_AI
        self.timeout = 240.0

    async def send_request(self, model: str, prompt: str, system_prompt: str) -> str:
        async with AsyncClient(timeout=self.timeout) as client:
            try:
                result = await client.post(
                    url=self.url_ai,
                    headers=self.headers,
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "system",
                                "content": system_prompt,
                            },
                            {"role": "user", "content": prompt},
                        ],
                    },
                )

                return result.json()["choices"][0]["message"]["content"]
            except ReadTimeout:
                raise ReadTimeout("Timeout reached")
            except HTTPStatusError as e:
                raise Exception(f"HTTP status error: {e.response.status_code}")
            except Exception as e:
                raise Exception(f"Unexpected error: {e}")

    async def deepseek(self, prompt: str, system_prompt: str) -> str:
        return await self.send_request("deepseek-v3.2", prompt, system_prompt)

    async def gemini(self, prompt: str, system_prompt: str) -> str:
        return await self.send_request("gemini-3-pro", prompt, system_prompt)

    async def claude(self, prompt: str, system_prompt: str) -> str:
        return await self.send_request("claude-4.6-opus", prompt, system_prompt)


ai = AI()

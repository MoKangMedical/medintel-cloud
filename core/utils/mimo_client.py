"""
MIMO API 统一客户端
所有服务共享的模型调用层
"""

from __future__ import annotations
from typing import Optional
import httpx
from pydantic import BaseModel


class MIMOConfig(BaseModel):
    base_url: str = "https://api.xiaomimimo.com/v1"
    api_key: str = ""
    default_model: str = "mimo-v2-pro"
    timeout: int = 120


class MIMOClient:
    """统一 MIMO API 客户端"""

    def __init__(self, config: Optional[MIMOConfig] = None):
        self.config = config or MIMOConfig()
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers={"Authorization": f"Bearer {self.config.api_key}"},
            timeout=self.config.timeout,
        )

    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str:
        """标准聊天补全"""
        resp = await self._client.post(
            "/chat/completions",
            json={
                "model": model or self.config.default_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    async def embed(self, texts: list[str], model: str = "mimo-v2-omni") -> list[list[float]]:
        """文本嵌入"""
        resp = await self._client.post(
            "/embeddings",
            json={"model": model, "input": texts},
        )
        resp.raise_for_status()
        return [item["embedding"] for item in resp.json()["data"]]

    async def close(self):
        await self._client.aclose()


def get_mimo_client() -> MIMOClient:
    """FastAPI 依赖注入"""
    return MIMOClient()

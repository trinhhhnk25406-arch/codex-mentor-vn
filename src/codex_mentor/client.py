"""OpenAI API Client ổn định, tương thích toàn bộ hệ sinh thái SDK v1.x."""
from __future__ import annotations

import os
from typing import Any, Dict, Iterator, Optional
from openai import OpenAI
from .prompts import SYSTEM_BASE
from .utils import CLIError, extract_json

DEFAULT_MODEL = os.getenv("CODEX_MODEL", "gpt-4o")


class CodexClient:
    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None) -> None:
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise CLIError(
                "Không tìm thấy OPENAI_API_KEY.\n"
                "Vui lòng thiết lập biến môi trường hoặc tạo tệp .env (tham khảo .env.example)."
            )
        self.client = OpenAI(api_key=key)
        self.model = model or DEFAULT_MODEL

    def ask_json(self, prompt: str, temperature: float = 0.2) -> Dict[str, Any]:
        """Gọi OpenAI với định dạng phản hồi bắt buộc là JSON Object."""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_BASE},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return extract_json(content)

    def stream_text(self, prompt: str, temperature: float = 0.2) -> Iterator[str]:
        """Gọi OpenAI ở chế độ Streaming truyền chunk văn bản theo thời gian thực."""
        stream = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            stream=True,
            messages=[
                {"role": "system", "content": SYSTEM_BASE},
                {"role": "user", "content": prompt},
            ],
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def ask_text(self, prompt: str, temperature: float = 0.2) -> str:
        """Gọi OpenAI nhận toàn bộ khối văn bản."""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": SYSTEM_BASE},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""

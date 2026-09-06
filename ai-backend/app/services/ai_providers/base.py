"""
الواجهة الأساسية لأي مزوّد ذكاء اصطناعي — كل مزوّد (OpenAI, Anthropic, Gemini...)
يطبّق نفس الواجهة عشان routers/chat.py ما يهتم بأي مزوّد يشتغل خلفها
"""
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class AIReply:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class AIProvider(ABC):
    @abstractmethod
    async def get_reply(
        self, message: str, history: list[dict[str, str]] | None = None
    ) -> AIReply:
        """يرجّع الرد كاملًا دفعة وحدة، مع عدد التوكنز لو المزوّد يوفّره"""
        raise NotImplementedError

    @abstractmethod
    def stream_reply(
        self, message: str, history: list[dict[str, str]] | None = None
    ) -> AsyncIterator[str]:
        """يرجّع الرد على شكل أجزاء نصية تدريجيًا (streaming) — بدون عدد توكنز
        (تتبّعه أثناء البث يختلف بصيغة لكل مزوّد، خارج نطاق هذي المرحلة)"""
        raise NotImplementedError

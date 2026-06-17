from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from django.conf import settings
from django.utils import timezone

from core.exceptions import AIAnalysisError
from core.logger import ai_logger


DEFAULT_TAGS = [
    "smart_farm",
    "youth_farmer",
    "startup",
    "education",
    "rd",
    "investment",
    "export",
    "competition",
    "agriculture_tech",
    "digital_agriculture",
]

DEFAULT_RECOMMENDED_FOR = [
    "student",
    "youth_farmer",
    "pre_startup",
    "startup",
    "farm_company",
    "agri_corporation",
    "agri_tech_company",
]


ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {
            "type": "string",
            "description": "A concise Korean summary in exactly three short lines.",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string", "enum": DEFAULT_TAGS},
            "minItems": 1,
            "maxItems": 6,
        },
        "importance_score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
        },
        "recommended_for": {
            "type": "array",
            "items": {"type": "string", "enum": DEFAULT_RECOMMENDED_FOR},
            "minItems": 1,
            "maxItems": 5,
        },
    },
    "required": ["summary", "tags", "importance_score", "recommended_for"],
}


@dataclass(frozen=True)
class NoticeAnalysisResult:
    summary: str
    tags: list[str]
    importance_score: int
    recommended_for: list[str]
    provider: str = "openai"

    def to_notice_updates(self) -> dict[str, Any]:
        return {
            "ai_summary": self.summary,
            "ai_tags": self.tags,
            "importance_score": self.importance_score,
            "recommended_for": self.recommended_for,
            "ai_analyzed_at": timezone.now(),
        }


class OpenAINoticeAnalyzer:
    """Analyze agricultural support notices with OpenAI, with a safe local fallback."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        use_fallback: bool = True,
    ) -> None:
        config = getattr(settings, "AI_CONFIG", {})
        self.api_key = api_key if api_key is not None else config.get("api_key", "")
        self.model = model or config.get("model", "gpt-4.1-mini")
        self.temperature = temperature if temperature is not None else config.get("temperature", 0.2)
        self.max_tokens = max_tokens or config.get("max_tokens", 700)
        self.use_fallback = use_fallback
        self._client = None

    @property
    def client(self):
        if self._client is not None:
            return self._client

        if not self.api_key:
            raise AIAnalysisError("OPENAI_API_KEY is not configured.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AIAnalysisError("openai package is not installed.") from exc

        self._client = OpenAI(api_key=self.api_key)
        return self._client

    def analyze_notice_data(self, notice: dict[str, Any]) -> NoticeAnalysisResult:
        prompt = self._build_prompt(notice)

        try:
            result = self._analyze_with_responses_api(prompt)
            return self._normalize_result(result, provider="openai")
        except Exception as responses_exc:
            ai_logger.info("Responses API analysis skipped: %s", responses_exc)

        try:
            result = self._analyze_with_chat_completions(prompt)
            return self._normalize_result(result, provider="openai")
        except Exception as chat_exc:
            if not self.use_fallback:
                raise AIAnalysisError(str(chat_exc)) from chat_exc
            ai_logger.warning("OpenAI analysis failed, using fallback: %s", chat_exc)
            return self._fallback_analysis(notice)

    def analyze_notice(self, notice: Any, save: bool = True) -> NoticeAnalysisResult:
        notice_data = {
            "agency": getattr(getattr(notice, "agency", None), "name", ""),
            "title": getattr(notice, "title", ""),
            "category": getattr(notice, "category", ""),
            "summary": getattr(notice, "summary", ""),
            "content": getattr(notice, "content", ""),
            "posted_date": getattr(notice, "posted_date", ""),
            "deadline": getattr(notice, "deadline", ""),
            "url": getattr(notice, "url", ""),
        }
        result = self.analyze_notice_data(notice_data)

        if save:
            updates = result.to_notice_updates()
            for field, value in updates.items():
                setattr(notice, field, value)
            notice.save(update_fields=[*updates.keys(), "updated_at"])

        return result

    def analyze_queryset(self, queryset: Any, limit: int = 50) -> list[NoticeAnalysisResult]:
        results: list[NoticeAnalysisResult] = []
        for notice in queryset[:limit]:
            try:
                results.append(self.analyze_notice(notice, save=True))
            except Exception as exc:
                ai_logger.error("Failed to analyze notice %s: %s", getattr(notice, "pk", None), exc)
        return results

    def _analyze_with_responses_api(self, prompt: str) -> dict[str, Any]:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": self._system_prompt(),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "notice_analysis",
                    "schema": ANALYSIS_SCHEMA,
                    "strict": True,
                }
            },
            max_output_tokens=self.max_tokens,
        )

        output_text = getattr(response, "output_text", "")
        if not output_text:
            output_text = self._extract_response_text(response)

        return json.loads(output_text)

    def _analyze_with_chat_completions(self, prompt: str) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    def _normalize_result(self, result: dict[str, Any], provider: str) -> NoticeAnalysisResult:
        tags = [tag for tag in result.get("tags", []) if tag in DEFAULT_TAGS]
        recommended_for = [
            target
            for target in result.get("recommended_for", [])
            if target in DEFAULT_RECOMMENDED_FOR
        ]
        score = int(result.get("importance_score", 50))

        return NoticeAnalysisResult(
            summary=str(result.get("summary", "")).strip(),
            tags=tags[:6] or ["agriculture_tech"],
            importance_score=max(0, min(100, score)),
            recommended_for=recommended_for[:5] or ["student"],
            provider=provider,
        )

    def _fallback_analysis(self, notice: dict[str, Any]) -> NoticeAnalysisResult:
        title = str(notice.get("title", ""))
        content = str(notice.get("content") or notice.get("summary") or "")
        text = f"{title} {content}".lower()

        tags: list[str] = []
        keyword_map = {
            "smart_farm": ("스마트팜", "smart farm", "ict", "디지털농업"),
            "youth_farmer": ("청년농", "청년", "후계농"),
            "startup": ("창업", "스타트업", "사업화"),
            "education": ("교육", "훈련", "과정", "세미나"),
            "rd": ("r&d", "연구", "기술개발", "실증"),
            "investment": ("투자", "자금", "융자"),
            "export": ("수출", "해외"),
            "competition": ("경진", "공모", "대회", "콘테스트"),
            "agriculture_tech": ("농업기술", "기술", "농업"),
            "digital_agriculture": ("디지털", "데이터", "ai", "인공지능"),
        }

        for tag, keywords in keyword_map.items():
            if any(keyword in text for keyword in keywords):
                tags.append(tag)

        tags = tags[:6] or ["agriculture_tech"]
        recommended_for = self._fallback_recommended_for(text)
        importance_score = self._fallback_importance_score(text, tags)
        summary = self._fallback_summary(title, content)

        return NoticeAnalysisResult(
            summary=summary,
            tags=tags,
            importance_score=importance_score,
            recommended_for=recommended_for,
            provider="fallback",
        )

    def _fallback_recommended_for(self, text: str) -> list[str]:
        targets: list[str] = []
        if any(word in text for word in ("대학생", "학생", "교육", "인턴")):
            targets.append("student")
        if any(word in text for word in ("청년", "청년농", "후계농")):
            targets.append("youth_farmer")
        if any(word in text for word in ("예비창업", "창업", "사업화")):
            targets.append("pre_startup")
            targets.append("startup")
        if any(word in text for word in ("농업법인", "농업회사", "법인")):
            targets.append("agri_corporation")
        if any(word in text for word in ("기술기업", "스타트업", "벤처")):
            targets.append("agri_tech_company")

        return list(dict.fromkeys(targets))[:5] or ["student", "pre_startup"]

    def _fallback_importance_score(self, text: str, tags: list[str]) -> int:
        score = 45
        weighted_keywords = {
            "스마트팜": 15,
            "창업": 12,
            "청년": 10,
            "교육": 8,
            "지원": 8,
            "사업화": 10,
            "r&d": 8,
            "기술개발": 8,
            "자금": 8,
        }

        for keyword, weight in weighted_keywords.items():
            if keyword in text:
                score += weight

        score += min(len(tags), 4) * 3
        return max(0, min(100, score))

    def _fallback_summary(self, title: str, content: str) -> str:
        lines = [title.strip()]
        if content:
            compact = " ".join(content.split())
            lines.append(compact[:120])
        lines.append("스마트팜 창업 준비생과 농업 관련 학습자가 검토할 만한 공고입니다.")
        return "\n".join(line for line in lines if line)[:600]

    def _build_prompt(self, notice: dict[str, Any]) -> str:
        payload = {
            "agency": str(notice.get("agency", "")),
            "title": str(notice.get("title", "")),
            "category": str(notice.get("category", "")),
            "content": str(notice.get("content") or notice.get("summary") or "")[:1000],
        }
        return json.dumps(payload, ensure_ascii=False)

    def _system_prompt(self) -> str:
        return (
            "You analyze Korean agricultural, smart-farm, startup, education, "
            "contest, and R&D notices. Return only valid JSON matching the schema. "
            "The summary must be Korean and exactly three short lines. "
            "Score usefulness for smart-farm startup candidates and agriculture-related "
            "college students from 0 to 100."
        )

    def _extract_response_text(self, response: Any) -> str:
        output = getattr(response, "output", None) or []
        chunks: list[str] = []
        for item in output:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    chunks.append(text)
        return "".join(chunks)


def analyze_notice_data(notice: dict[str, Any]) -> dict[str, Any]:
    analyzer = OpenAINoticeAnalyzer()
    return asdict(analyzer.analyze_notice_data(notice))

import json
import re

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from enum import Enum
from dataclasses import dataclass
from typing import Optional
load_dotenv()

class GuardrailResult(Enum):
    PASS = "pass"
    BLOCK = "block"
    REDIRECT = "redirect"
    ERROR = "error"


@dataclass
class GuardrailResponse:
    result: GuardrailResult
    message: Optional[str] = None
    suggestion: Optional[str] = None

GUARDRAIL_PROMPT = PromptTemplate.from_template("""
You are a strict but reasonable input guardrail for a Travel Assistant.

Your task:
Analyze the user query and classify it.

Rules:
- Be conservative with safety: if illegal or harmful → safety = "fail"

- Travel relevance includes BOTH:
  a) Explicit travel topics:
     cities, countries, routes, hotels, food, weather, attractions
  b) Implicit or soft travel intent, such as:
     desire to relax, go on a trip, spend a weekend away,
     explore somewhere, take a break, vacation planning,
     even if no location is mentioned yet

- If the query expresses a general desire to travel or relax,
  but lacks details → relevance = "pass" (NOT fail)

- Only mark relevance = "fail" if the query is clearly unrelated to travel
  (e.g. programming, math, politics, general life advice)

- Logic error means geographic or real-world impossibility
  (e.g. traveling between impossible locations)

- Scope = "ua" ONLY if the main focus is Ukraine
  If no country or city is mentioned → scope = "unknown"

User query:
"{query}"

Return ONLY valid JSON in this exact format:

{{
  "safety": "pass" | "fail",
  "relevance": "pass" | "fail",
  "logic_error": null | "short explanation",
  "scope": "ua" | "foreign" | "unknown",
  "confidence": "high" | "medium" | "low"
}}
""")


class LLMTravelInputGuardrails:
    def __init__(self, model_name: str = "gpt-4o"):
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0,
        )

    def check(self, query: str) -> GuardrailResponse:
        raw = self.llm.invoke(
            GUARDRAIL_PROMPT.format(query=query)
        )

        try:
            data = self._safe_json_parse(raw.content)
        except Exception:
            return GuardrailResponse(
                result=GuardrailResult.ERROR,
                message="Failed to validate request.",
                suggestion="Please rephrase your travel question."
            )

        return self._map_to_response(data)

    def _map_to_response(self, data: dict) -> GuardrailResponse:

        if data["safety"] == "fail":
            return GuardrailResponse(
                result=GuardrailResult.BLOCK,
                message="I can't help with illegal or unsafe activities.",
                suggestion="I can help with safe and legal travel advice."
            )

        if data["relevance"] == "fail":
            return GuardrailResponse(
                result=GuardrailResult.REDIRECT,
                message="I specialize in travel-related questions.",
                suggestion="Ask me about trips, cities, routes, or attractions."
            )

        if data["logic_error"]:
            return GuardrailResponse(
                result=GuardrailResult.ERROR,
                message=data["logic_error"],
                suggestion="Would you like a realistic alternative?"
            )

        if data["scope"] == "foreign":
            return GuardrailResponse(
                result=GuardrailResult.REDIRECT,
                message="This assistant focuses on travel within Ukraine 🇺🇦.",
                suggestion="I can recommend similar destinations in Ukraine."
            )

        return GuardrailResponse(result=GuardrailResult.PASS)

    def _safe_json_parse(self, content: str) -> dict:
        cleaned = re.sub(r"^```json|```$", "", content.strip(), flags=re.MULTILINE)
        return json.loads(cleaned)
import base64
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _messages_from_history(history: list[dict]) -> list:
    """Convert list of {role, content} to LangChain messages."""
    result = []
    for m in history:
        role, content = m.get("role"), m.get("content", "")
        if role == "user":
            result.append(HumanMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))
    return result


duckduckgo_tool = DuckDuckGoSearchRun()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    api_key=OPENAI_API_KEY,
)

def image_to_base64(file) -> str:
    if hasattr(file, "read"):
        return base64.b64encode(file.read()).decode("utf-8")
    return base64.b64encode(file).decode("utf-8")


VALIDATION_HISTORY_LIMIT = 12  # last N messages to include for context (6 exchanges)


def _is_medical_query(query: str, history=None) -> bool:
    """Returns True if the query is about medicine/health. Uses conversation history for context."""
    if not (query and query.strip()):
        return False
    prompt = _load_prompt("validation")
    if not prompt:
        return True

    history_messages = _get_history_messages(history) if history else []
    # Take last N messages so validator sees recent context (e.g. "а які аналоги?" after drug question)
    recent = history_messages[-VALIDATION_HISTORY_LIMIT:] if history_messages else []

    if not recent:
        user_content = query.strip()[:500]
    else:
        context_lines = []
        for m in recent:
            role = "Користувач" if (getattr(m, "type", None) == "human") else "Асистент"
            text = (getattr(m, "content", None) or (m.get("content", "") if isinstance(m, dict) else ""))[:300]
            context_lines.append(f"{role}: {text}")
        context_block = "\n".join(context_lines)
        user_content = (
            "Контекст розмови:\n" + context_block + "\n\nПоточне повідомлення користувача: " + query.strip()[:500]
        )

    response = llm.invoke(
        [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_content},
        ]
    )
    answer = (response.content or "").strip().upper()
    return "YES" in answer


NON_MEDICAL_REPLY = (
    "Це питання не стосується ліків чи медичної інформації. "
    "Я можу допомогти лише з питаннями про препарати, дозування та медичну інформацію. "
    "Задайте, будь ласка, питання про ліки або надішліть фото упаковки/інструкції."
)


def medical_image_tool(image_b64: str, question: str, history_messages=None) -> str:
    system_content = _load_prompt("image_analysis") or (
        "You are a medical assistant specialized in identifying medicines from images. "
        "Identify the medicine, provide name, use, dosage, contraindications. "
        "Always add a disclaimer to consult a doctor. Do not hallucinate drug names."
    )
    messages = [{"role": "system", "content": system_content}]

    if history_messages:
        for m in history_messages:
            if hasattr(m, "content"):
                role = "user" if m.type == "human" else "assistant"
                messages.append({"role": role, "content": m.content})
            else:
                messages.append({"role": m.get("role"), "content": m.get("content", "")})

    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": question or "Що це за препарат?"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
            },
        ],
    })

    response = llm.invoke(messages)
    return response.content


@tool("MedicalImageAnalysis")
def medical_image_analysis_tool(image_base64: str, question: str) -> str:
    """
    Use this to analyze medical-related images such as medicine packaging
    or instruction leaflets. Input must include image_base64 and question.
    """
    return medical_image_tool(
        image_b64=image_base64,
        question=question,
    )

@tool
def drug_lookup(drug_name: str) -> str:
    """Search official drug info using OpenFDA API."""
    url = f"https://api.fda.gov/drug/label.json?search=openfda.brand_name:{drug_name}&limit=1"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()

        if "results" not in data:
            return "No official drug data found."

        item = data["results"][0]

        return f"""
Name: {drug_name}
Indications: {item.get('indications_and_usage', ['N/A'])[0][:500]}
Dosage: {item.get('dosage_and_administration', ['N/A'])[0][:500]}
Contraindications: {item.get('contraindications', ['N/A'])[0][:500]}
"""
    except Exception as e:
        return f"Error querying drug database: {str(e)}"


tools = [medical_image_analysis_tool, drug_lookup, duckduckgo_tool] + load_tools(["wikipedia"])

_system_prompt = _load_prompt("system")
system_prompt = _system_prompt or (
    "You are a medical information assistant. Help identify medicines and provide "
    "cautious, factual information. Always cite sources. Never invent drug names."
)

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt,
)


def _get_history_messages(history) -> list:
    """Normalize history to list of LangChain messages (for agent)."""
    if hasattr(history, "messages"):
        return list(history.messages)
    if isinstance(history, list) and history:
        # Already LangChain messages (have .type); dicts from API have "role" key
        first = history[0]
        if isinstance(first, dict):
            return _messages_from_history(history)
        return list(history)
    if isinstance(history, list):
        return []
    return []


def answer_query(
    query: str,
    history,
    image_file=None,
    image_base64: str | None = None,
) -> str:
    """
    Answer a medical query. history can be StreamlitChatMessageHistory
    or list of {"role": "user"|"assistant", "content": str}.
    """
    if image_file is not None:
        image_b64 = image_to_base64(image_file)
    elif image_base64:
        image_b64 = image_base64
    else:
        image_b64 = None

    if image_b64 is not None:
        h = _get_history_messages(history)
        return medical_image_tool(
            image_b64=image_b64,
            question=query or "Що це за препарат?",
            history_messages=h,
        )

    messages = _get_history_messages(history)
    if not _is_medical_query(query, history=messages):
        return NON_MEDICAL_REPLY

    messages.append(HumanMessage(content=query))

    result = agent.invoke({"messages": messages})
    return result["messages"][-1].content

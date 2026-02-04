import asyncio

from dotenv import load_dotenv
from langchain_community.tools import TavilySearchResults
from langchain_core.tools import Tool, StructuredTool
import time
from typing import Dict, Tuple
from pydantic import BaseModel, Field
from typing import Literal

load_dotenv()

SEARCH_CACHE: Dict[str, Tuple[float, str]] = {}
CACHE_TTL = 60 * 10

class InternetSearchInput(BaseModel):
    query: str = Field(
        description="Search query, natural language"
    )
    search_depth: Literal["basic", "advanced"] = Field(
        default="basic",
        description="Search depth: basic or advanced"
    )

def search_internet(query: str, search_depth: str = "basic") -> str:
    """Search for up-to-date information on the internet"""

    if search_depth not in ("basic", "advanced"):
        search_depth = "basic"

    tavily = TavilySearchResults(
        max_results=5 if search_depth == "basic" else 10,
        search_depth=search_depth,
        include_answer=True,
        include_raw_content=False,
    )

    now = time.time()
    cache_key = f"{query}:{search_depth}"

    if cache_key in SEARCH_CACHE:
        ts, cached_result = SEARCH_CACHE[cache_key]
        if now - ts < CACHE_TTL:
            print("🧠 Using cached search result")
            return f"🧠 Cached result:\n\n{cached_result}"
        else:
            del SEARCH_CACHE[cache_key]

    try:
        results = tavily.invoke(query)

        if not results:
            return "No results found."

        SEARCH_CACHE[cache_key] = (now, results)

        formatted = []
        for r in results:
            formatted.append(
                f"**{r['title']}**\n"
                f"{r['content']}\n"
                f"🔗 {r['url']}"
            )

        return "\n\n---\n\n".join(formatted)

    except Exception as e:
        msg = str(e).lower()
        if "rate limit" in msg or "quota" in msg:
            return "⚠️ Internet search temporarily unavailable (API limit reached)."
        elif "connection" in msg or "network" in msg or "timeout" in msg:
            return "⚠️ Internet search unavailable (network issue)."
        else:
            return f"⚠️ Internet search failed: {str(e)}"

async def search_internet_async(
    query: str,
    search_depth: str = "basic",
) -> str:
    return await asyncio.to_thread(
        search_internet,
        query,
        search_depth,
    )

internet_search_tool = StructuredTool.from_function(
    func=search_internet_async,
    name="internet_search",
    description="""
Search for up-to-date information on the internet.

Use search_depth:
- basic: weather, opening hours, quick facts
- advanced: events, prices, schedules, comparisons
""",
    args_schema=InternetSearchInput,
)
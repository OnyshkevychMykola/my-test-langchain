from dotenv import load_dotenv
import asyncio

from pydantic import BaseModel, Field
from fastmcp import Client

from langchain_openai import ChatOpenAI
from langchain_classic.tools import StructuredTool
from langchain_classic.agents import (
    create_openai_functions_agent,
    AgentExecutor,
)
from langchain_classic.prompts import ChatPromptTemplate

import rag_tool
from ask_human import ask_human_tool
from memory import SimpleWindowMemory
from prompt import SYSTEM_PROMPT
from search import internet_search_tool

load_dotenv()
class CheckAvailabilityArgs(BaseModel):
    restaurant: str = Field(..., description="Restaurant key, e.g. 'bachevski'")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    time: str = Field(..., description="Time in HH:MM format")
    guests: int = Field(..., description="Number of guests")


class MakeReservationArgs(BaseModel):
    restaurant: str
    date: str
    time: str
    guests: int
    name: str
    phone: str


class CancelReservationArgs(BaseModel):
    reservation_id: str


class ListReservationsArgs(BaseModel):
    phone: str

class SearchRestaurantsArgs(BaseModel):
    query: str = Field(..., description="User query about restaurants")

async def main():
    client = Client("mcp_server.py")

    async with client:
        tools = []

        # ---------- runners ----------

        async def check_availability_runner(**kwargs):
            return await client.call_tool("check_availability", kwargs)

        async def make_reservation_runner(**kwargs):
            return await client.call_tool("make_reservation", kwargs)

        async def cancel_reservation_runner(**kwargs):
            return await client.call_tool("cancel_reservation", kwargs)

        async def list_reservations_runner(**kwargs):
            return await client.call_tool("list_reservations", kwargs)

        async def list_restaurants_runner():
            return await client.read_resource("restaurants://list")

        async def search_restaurants_runner(query: str) -> str:
            return rag_tool.search_restaurants(query)
        # ---------- tools ----------

        tools += [
            StructuredTool.from_function(
                coroutine=check_availability_runner,
                name="check_availability",
                description="Check table availability in a restaurant",
                args_schema=CheckAvailabilityArgs,
            ),
            StructuredTool.from_function(
                coroutine=make_reservation_runner,
                name="make_reservation",
                description="Make a reservation",
                args_schema=MakeReservationArgs,
            ),
            StructuredTool.from_function(
                coroutine=cancel_reservation_runner,
                name="cancel_reservation",
                description="Cancel a reservation",
                args_schema=CancelReservationArgs,
            ),
            StructuredTool.from_function(
                coroutine=list_reservations_runner,
                name="list_reservations",
                description="List reservations by phone number",
                args_schema=ListReservationsArgs,
            ),
            StructuredTool.from_function(
                coroutine=list_restaurants_runner,
                name="list_restaurants",
                description="Show all available restaurants",
            ),
            StructuredTool.from_function(
                coroutine=search_restaurants_runner,
                name="search_restaurants",
                description="""
                Search information about restaurants in Ukraine.

                Use this tool when the user asks about:
                - restaurants in a city
                - menus
                - prices
                - addresses
                - opening hours
                - cuisine types
                - recommendations
                - price categories
                """,
                args_schema=SearchRestaurantsArgs,
            ),
            internet_search_tool,
            ask_human_tool,
        ]

        # ---------- LLM ----------

        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    SYSTEM_PROMPT,
                ),
                ("placeholder", "{history}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        )

        agent = create_openai_functions_agent(
            llm=llm,
            tools=tools,
            prompt=prompt,
        )

        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
        )

        # ---------- CLI loop ----------

        memory = SimpleWindowMemory(k=10)

        print("🍽 Restaurant Booking Assistant (with memory)")
        print("Type 'exit' or 'clear' to reset memory\n")

        while True:
            try:
                user_input = input("👤 You: ").strip()

                if user_input.lower() in {"exit", "quit"}:
                    print("👋 Bye!")
                    break

                if user_input.lower() == "clear":
                    memory.clear()
                    print("🧹 Memory cleared\n")
                    continue

                if not user_input:
                    continue

                memory.add_user(user_input)

                result = await executor.ainvoke(
                    {
                        "input": user_input,
                        "history": memory.get_messages(),
                    }
                )

                output = result["output"]

                print(f"\n🤖 Assistant: {output}\n")

                # ➜ add AI message
                memory.add_ai(output)

            except KeyboardInterrupt:
                print("\n👋 Bye!")
                break



if __name__ == "__main__":
    asyncio.run(main())
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain_openai import ChatOpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model="gpt-4o",
    streaming=True
)

tools = load_tools(["wikipedia"])

react_system_prompt = """
You are a ReAct-style AI agent.

Follow this loop carefully:
THOUGHT → ACTION → OBSERVATION
until final answer.
"""

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=react_system_prompt
)

question = input("Your question: ")

for event in agent.stream(
    {
        "messages": [
            {"role": "user", "content": question}
        ]
    }
):
    print(event)
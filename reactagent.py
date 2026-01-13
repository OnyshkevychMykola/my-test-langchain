import os
from dotenv import load_dotenv

from langchain.tools import tool
from langchain_classic import hub
from langchain_classic.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI

load_dotenv()

@tool
def multiply(input: str) -> int:
    """Множить два числа. Формат: '12, 7'"""
    a, b = map(int, input.replace("(", "").replace(")", "").split(","))
    return a * b

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model="gpt-4o",
)

tools = [multiply]

prompt = hub.pull("hwchase17/react")

agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True
)

if __name__ == "__main__":
    result = agent_executor.invoke({
        "input": "Скільки буде 12 помножити на 7?"
    })

    print(result)
    print(result["output"])

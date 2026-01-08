import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain_openai import ChatOpenAI

load_dotenv()


OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(api_key=OPENAI_API_KEY, model='gpt-4o')
tools =  load_tools(["wikipedia"])
react_system_prompt = """
You are a ReAct-style AI agent.

Follow this loop carefully:
1. THOUGHT: Think step by step about what to do next.
2. ACTION: When needed, call one of the tools (wikipedia, ddg-search).
3. OBSERVATION: Read the tool result and decide the next step.

Repeat THOUGHT → ACTION → OBSERVATION
until you are ready to give the final answer.

When you are confident, stop using tools and respond with a clear, concise final answer to the user.
"""
agent = create_agent(
model=llm,
    tools = tools,
    system_prompt=react_system_prompt
)

print("Chat with Document")
question=input("Your Question")

if question:
    result = agent.invoke(
        {
            "messages":[{"role":"user","content":question}]
        }
    )
    final_msg = result["messages"][-1]
    print(result)
    print(final_msg.content)
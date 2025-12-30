import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain.agents import create_agent
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_core.tools import Tool
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain_community.chat_message_histories import StreamlitChatMessageHistory

from indexing import build_retriever

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    api_key=OPENAI_API_KEY
)
embeddings = OpenAIEmbeddings()

retriever = build_retriever()

rag_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", """
You answer questions using only the provided context.
If there isn’t enough information → say: "I don’t know from memory."
Do not make things up.
Do not add information outside the context.
The answer must be concise.

Context:
{context}
        """),
        ("human", "{input}"),
    ]
)

qa_chain = create_stuff_documents_chain(llm, rag_prompt)
rag_chain = create_retrieval_chain(retriever, qa_chain)

history = StreamlitChatMessageHistory(key="chat_history")


def rag_tool_function(query: str) -> str:
    response = rag_chain.invoke({"input": query})
    return response["answer"]


rag_tool = Tool(
    name="RAGContext",
    func=rag_tool_function,
    description="Use this to answer questions about Mykola Onyshkevych or personal info."
)

tools = [rag_tool] + load_tools(["wikipedia"])

system_prompt = """
You are a ReAct-style AI agent with access to personal context documents (RAG) and external tools.

Rules:
1. If the question is about "Mykola Onyshkevych" or uses "I", "me", "my" referring to the user,
   answer ONLY by calling the RAGContext tool.
2. For other questions, you may use external tools (wikipedia).
3. Follow the ReAct loop: THOUGHT → ACTION → OBSERVATION → THOUGHT until ready.
4. Do not make things up. Be concise.
"""

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt,
)

def answer_query(query: str):
    result = agent.invoke({"messages": history.messages + [{"role": "user", "content": query}]})
    return result["messages"][-1].content

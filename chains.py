import base64
import os
import streamlit as st

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain.agents import create_agent
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_core.tools import Tool
from langchain_community.agent_toolkits.load_tools import load_tools

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
You are a medical information assistant.

Use ONLY the provided context.
If the information is not present → say:
"I don’t have enough reliable information to answer this."

Do NOT:
- diagnose
- recommend treatment
- suggest dosages

Use cautious language.
Context:
{context}
        """),
        ("human", "{input}"),
    ]
)

qa_chain = create_stuff_documents_chain(llm, rag_prompt)
rag_chain = create_retrieval_chain(retriever, qa_chain)

def medical_domain_guard(query: str) -> bool:
    prompt = f"""
Is the following user question related to medicine or health?

Answer ONLY "yes" or "no".

Question:
{query}
"""
    result = llm.invoke(prompt)
    return "yes" in result.content.lower()

MEDICAL_REFUSAL = (
    "I can only help with medical or health-related information. "
    "Please ask a question related to medicine."
)

def image_to_base64(file) -> str:
    return base64.b64encode(file.read()).decode("utf-8")

def rag_tool_function(query: str) -> str:
    response = rag_chain.invoke({"input": query})
    return response["answer"]


rag_tool = Tool(
    name="RAGContext",
    func=rag_tool_function,
    description="Use this to answer questions about Mykola Onyshkevych or personal info."
)

def medical_image_tool(image_b64: str, question: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a medical information assistant.\n"
                "Describe what you see cautiously.\n"
                "Do NOT identify dosages.\n"
                "Do NOT give medical advice.\n"
                "Use uncertainty language."
            ),
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_b64}"
                    },
                },
            ],
        },
    ]

    response = llm.invoke(messages)
    return response.content

def medical_image_tool_wrapper(inputs: dict) -> str:
    return medical_image_tool(
        image_b64=inputs["image_base64"],
        question=inputs["question"],
    )


medical_image_analysis_tool = Tool(
    name="MedicalImageAnalysis",
    func=medical_image_tool_wrapper,
    description=(
        "Use this to analyze medical-related images such as medicine packaging "
        "or instruction leaflets. Input must include image_base64 and question."
    ),
)


tools = [rag_tool, medical_image_analysis_tool] + load_tools(["wikipedia"])

system_prompt = """
You are a medical information assistant.

Rules:
- You provide general medical information only.
- You do NOT diagnose.
- You do NOT prescribe treatment or dosages.
- You do NOT replace a doctor.
- If the question asks what to take, how much, or gives a diagnosis → refuse.

You must:
- Use cautious language ("may", "can be associated with").
- Encourage consulting a healthcare professional when relevant.
- Be concise and factual.
"""

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt,
)

def answer_query(
    query: str,
    history,
    image_file=None,
):
    if not medical_domain_guard(query):
        return MEDICAL_REFUSAL

    if image_file is not None:
        image_b64 = image_to_base64(image_file)
        return medical_image_tool(
            image_b64=image_b64,
            question=query,
        )

    result = agent.invoke(
        {
            "messages": history.messages
            + [{"role": "user", "content": query}]
        }
    )

    return result["messages"][-1].content

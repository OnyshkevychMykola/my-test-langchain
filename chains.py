import base64
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.tools import Tool
from langchain_community.agent_toolkits.load_tools import load_tools


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    api_key=OPENAI_API_KEY
)

def image_to_base64(file) -> str:
    return base64.b64encode(file.read()).decode("utf-8")

def medical_image_tool(image_b64: str, question: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a medical information assistant.\n"
                "Carefully describe what is visible in the image.\n"
                "Use cautious, non-absolute language (e.g. \"may\", \"appears to\", \"could be\").\n"
                "Do not make assumptions beyond what can be observed."
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


tools = [medical_image_analysis_tool] + load_tools(["wikipedia"])

system_prompt = """
You are a medical information assistant with access to a RAGContext tool and external web sources.

Rules:
1. Always attempt to answer medical questions by calling the RAGContext tool first.
2. If the RAGContext tool does not contain relevant or sufficient information,
   you may search for reliable medical information on the internet (e.g. reputable health websites).
3. Use cautious, non-absolute language (e.g. "may", "can be associated with", "is often described as").
4. Do not invent facts or unsupported claims.
5. Be concise, factual, and neutral in tone.

Reasoning:
- Follow a ReAct-style loop internally (THOUGHT → ACTION → OBSERVATION → THOUGHT) when deciding
  whether to use RAGContext or external sources.
- Prefer information grounded in provided context over general web knowledge.
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

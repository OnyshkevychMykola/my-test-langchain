import base64
import os

import requests
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain_community.tools import DuckDuckGoSearchRun

duckduckgo_tool = DuckDuckGoSearchRun()

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    api_key=OPENAI_API_KEY
)

def image_to_base64(file) -> str:
    return base64.b64encode(file.read()).decode("utf-8")

def medical_image_tool(image_b64: str, question: str, history_messages=None) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a medical assistant specialized in identifying medicines from images.\n"
                "Your task:\n"
                "1. Try to identify the medicine name from the image.\n"
                "2. If medicine is identified, provide:\n"
                "- Name of the medicine\n"
                "- What it is used for\n"
                "- Typical dosage (adults / children if available)\n"
                "- Contraindications\n"
                "3. Always include a disclaimer advising to consult a doctor before use.\n"
                "4. Use cautious language: 'may', 'usually', 'often used', 'can be prescribed for'.\n"
                "5. If the image does NOT contain medicine or is unclear, say that you cannot identify it.\n"
                "6. Do NOT hallucinate drug names.\n"
            ),
        }
    ]

    if history_messages:
        messages.extend(history_messages)

    messages.append({
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

system_prompt = """
You are a medical information assistant.

Goals:
- Help identify medicines from images.
- Provide medical information cautiously and factually.

Rules:
1. Always try to ground medical information in external sources (tools, APIs, Wikipedia, search).
2. Every medical answer MUST include a section:
   "Sources:" with a list of where the information came from.
3. If no reliable sources were found, say clearly:
   "I could not find reliable sources to confirm this information."
4. Use cautious language ("may", "often used", "can be prescribed for").
5. If the image or question is not medical, reply that you do not have information.
6. Never invent drug names or medical facts.

If you used:
- Wikipedia → cite "Wikipedia"
- DuckDuckGo search → cite "DuckDuckGo Search"
- OpenFDA tool → cite "OpenFDA"
- Other APIs → cite their names
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
            history_messages=history.messages
        )

    result = agent.invoke(
        {
            "messages": history.messages
            + [{"role": "user", "content": query}]
        }
    )

    return result["messages"][-1].content

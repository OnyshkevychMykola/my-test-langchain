from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
import os
load_dotenv()

CHROMA_PATH = "./chroma_db"
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

app = FastMCP(name="chroma", port=8003)

# Initialize embeddings
embeddings = OpenAIEmbeddings(
    api_key=OPENAI_API_KEY
)

# Load existing Chroma DB
vectorstore = Chroma(
    persist_directory=CHROMA_PATH,
    embedding_function=embeddings
)

@app.tool()
def semantic_search(query: str, k: int = 5) -> dict:
    """
    Perform semantic search over the vector database.

    Use this tool ONLY when the user asks for information
    that may be stored in documents or knowledge base.

    Returns top matching documents.
    """
    if not query:
        return {
            "error": "empty_query"
        }

    results = vectorstore.similarity_search(query, k=k)

    return {
        "query": query,
        "results": [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in results
        ]
    }

if __name__ == "__main__":
    app.run(transport="streamable-http")

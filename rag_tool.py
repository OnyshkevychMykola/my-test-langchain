import os
from dotenv import load_dotenv

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()


CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "restaurants"
KB_DIR = "knowledge-base/restaurants/"


def build_retriever():
    embeddings = OpenAIEmbeddings(
        api_key=os.getenv("OPENAI_API_KEY")
    )

    if os.path.exists(CHROMA_DIR) and os.listdir(CHROMA_DIR):
        print("📦 Using existing Chroma database")

        vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME,
        )

    else:
        print("🧠 Creating new Chroma database")

        loader = DirectoryLoader(
            KB_DIR,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        )
        documents = loader.load()
        print(f"Loaded {len(documents)} documents")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", " ", ""],
        )
        chunks = splitter.split_documents(documents)
        print(f"Created {len(chunks)} chunks")

        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=CHROMA_DIR,
            collection_name=COLLECTION_NAME,
        )

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4},
    )

    return retriever


retriever = build_retriever()


def search_restaurants(query: str) -> str:
    """Search information about restaurants in Ukraine"""

    docs = retriever.invoke(query)

    if not docs:
        return "No restaurant information found in the knowledge base."

    results = []

    for doc in docs:
        source = doc.metadata.get("source", "unknown").split("/")[-1]
        results.append(
            f"[Source: {source}]\n{doc.page_content}"
        )

    return "\n\n---\n\n".join(results)
import os
from dotenv import load_dotenv
load_dotenv()
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def build_retriever():
    loader = DirectoryLoader("data", glob="*.txt")
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )
    chunks = splitter.split_documents(docs)

    embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings
    )

    retriever = vector_store.as_retriever(k=3)
    return retriever
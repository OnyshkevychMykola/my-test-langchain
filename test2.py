import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

from chains import rag_chain

OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")

loader = DirectoryLoader("data", glob="new.txt")
doc = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=20, chunk_overlap=2)
chunks = splitter.split_documents(doc)
embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings
    )

retriever = vector_store.as_retriever(k=3)

prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", """You are an assistant for answering questions.
    Use the provided context to respond.If the answer 
    isn't clear, acknowledge that you don't know. 
    Limit your response to three concise sentences.
    {context}

    """),
        ("human", "{input}")
    ]
)
llm = ChatOpenAI(api_key=OPENAI_API_KEY, model='gpt-4o')
qa_chain = create_stuff_documents_chain(llm, prompt_template)
rag_chain = create_retrieval_chain(retriever, qa_chain)

print("Chat with Document")
question=input("Your Question")

if question:
    response = rag_chain.invoke({"input":question})
    print(response['answer'])
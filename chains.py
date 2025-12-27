import os
from dotenv import load_dotenv
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.retrieval import create_retrieval_chain

from indexing import build_retriever

load_dotenv()
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings

retriever = build_retriever()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    api_key=OPENAI_API_KEY
)

embedding = OpenAIEmbeddings()

router_prompt = ChatPromptTemplate.from_template("""
You are classifying questions.

Important:

“yes” → if the question is about the identity or personal details of “Mykola Onyshkevych”.
“yes” → if the question uses “I”, “me”, “my” and contextually refers to the user (meaning Mykola Onyshkevych).
“no” → everything else.

Respond only with: yes or no (in English, with no additional words).

Examples:

“How old is Mykola Onyshkevych?” → yes
“How old am I?” → yes
“When is my birthday?” → yes
“What is the Pythagorean theorem?” → no
“When did World War II happen?” → no

Question: {question}
""")

router_chain = router_prompt | llm | StrOutputParser()


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


def answer_query(query: str):
    route = router_chain.invoke({"question": query}).strip().lower()
    if route == "yes":
        response = rag_chain.invoke({"input": query})
        return response["answer"]
    else:
        return llm.invoke(query).content
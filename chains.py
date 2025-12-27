import os
from dotenv import load_dotenv
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.retrieval import create_retrieval_chain

from indexing import build_retriever

load_dotenv()
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import OpenAIEmbeddings
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

retriever = build_retriever()
history = StreamlitChatMessageHistory(key="chat_history")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    api_key=OPENAI_API_KEY
)

basic_prompt = ChatPromptTemplate.from_messages([
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
])
llm_chain = basic_prompt | llm
llm_with_history = RunnableWithMessageHistory(
    llm_chain,
    lambda session_id: history,
    input_messages_key="input",
    history_messages_key="chat_history",
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

Question: {input}
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
MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ]
)

qa_chain = create_stuff_documents_chain(llm, rag_prompt)
rag_chain = create_retrieval_chain(retriever, qa_chain)


rag_chain_with_history = RunnableWithMessageHistory(
    rag_chain,
    lambda session_id : history,
    input_messages_key="input",
    history_messages_key="chat_history"
)


def answer_query(query: str, session_id: str):
    route = router_chain.invoke({"input": query}).strip().lower()
    if route == "yes":
        response = rag_chain_with_history.invoke(
            {"input": query},
            {"configurable": {"session_id": session_id}}
        )
        history.add_ai_message(response["answer"])
        return response["answer"]
    else:
        result = llm_with_history.invoke(
            {"input": query},
            {"configurable": {"session_id": session_id}}
        )
        return result.content

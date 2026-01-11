from time import time
from typing import Any

import requests
from dataclasses import dataclass

from langchain.agents.middleware.types import StateT, AgentState
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from langchain_classic.chat_models import init_chat_model
from langchain.tools import tool, ToolRuntime
from langchain_core.tools import create_retriever_tool
from langchain_openai import OpenAIEmbeddings
from langgraph.checkpoint.memory import InMemorySaver
from langchain_community.vectorstores import Chroma
from langchain.agents.middleware import ModelRequest, ModelResponse, dynamic_prompt, wrap_model_call, AgentMiddleware, \
    SummarizationMiddleware
from langgraph.runtime import Runtime
from langgraph.typing import ContextT

load_dotenv()
# ==========================================
# ==========================================
# STREAMING
# ==========================================
# ==========================================
# model = init_chat_model(model='gpt-4.1-mini')
#
# for chunk in model.stream('Hello, what is Python?'):
#     print(chunk.text, end='', flush=True)

# ==========================================
# ==========================================
# MEMORIZING AND RESPONSE FORMATTING
# ==========================================
# ==========================================
# @dataclass
# class Context:
#     user_id: str
#
# @dataclass
# class ResponseFormat:
#     summary: str
#     temperature_celsius: float
#     temperature_fahrenheit: float
#     humidity: float
#
# @tool('get_weather', description='Return weather information for a given city', return_direct=False)
# def get_weather(city: str):
#     response = requests.get(f'https://wttr.in/{city}?format=j1')
#     return response.json()
#
# @tool('locate_user', description='Look up a city user lives in, based on the context')
# def locate_user(runtime: ToolRuntime[Context]):
#     match runtime.context.user_id:
#         case 'ABC123':
#             return 'Viena'
#         case 'XYZ456':
#             return 'London'
#         case 'HJK111':
#                 return 'Paris'
#         case _:
#             return 'Unknown'
#
# model = init_chat_model(model='gpt-4.1-mini', temperature=0.3)
# checkpointer = InMemorySaver()
# agent = create_agent(
#     model=model,
#     tools=[get_weather, locate_user],
#     system_prompt='You are a helpful weather assistant, who always cracks and is humorous while remaining helpful ',
#     context_schema=Context,
#     response_format=ResponseFormat,
#     checkpointer=checkpointer,
# )
#
# config = { 'configurable': {'thread_id': 1}}
#
# response = agent.invoke(
#     {
#         'messages': [
#             { 'role': 'user', 'content': 'What is the weather like inj Vienna?'}
#         ],
#     },
#     config=config,
#     context=Context(user_id='ABC123'),
# )
#
# print(response['structured_response'].summary)
# print(response['structured_response'].temperature_celsius)

# ==========================================
# ==========================================
# IMAGES
# ==========================================
# ==========================================
# model = init_chat_model(model='gpt-4.1-mini')
#
# message={
#     'role': 'user',
#     'content': [
#         {'type': 'text', 'text': 'Describe the contents of this image.'},
#         # {'type': 'image', 'base64': b64encode(open(logo.png, 'rb').read()).decode, 'mime_type': 'image/png'},
#         {'type': 'image', 'url': 'https://upload.wikimedia.org/wikipedia/commons/7/72/Flag_Map_Of_Lviv_%28Ukraine%29.png'}
#     ]
# }
#
# response = model.invoke([message])
#
# print(response.content)

# ==========================================
# ==========================================
# RAG
# ==========================================
# ==========================================

# embeddings = OpenAIEmbeddings(model='text-embedding-3-large')
#
# texts = [
#     'Apple makes very good computers.',
#     'I believe Apple is innovative.',
#     'I love apples.',
#     'I am a fan of MacBooks.',
#     'I enjoy oranges.',
#     'I like Lenovo Thinkpads.',
#     'I think pears taste very good.',
# ]
#
# vector_store = Chroma.from_texts(texts, embedding=embeddings)
#
# retriever = vector_store.as_retriever(search_kwargs={'k':3})
#
# retriever_tool = create_retriever_tool(
#     retriever,
#     name='kb_search',
#     description='Search the small knowledge base for information')
#
# agent = create_agent(
#     model='gpt-4.1-mini',
#      tools=[retriever_tool],
#      system_prompt=(
#          "You are a helpful assistant. For questions about Macs, apples or laptops"
#          "first call the kb_search tool to retrieve context, then answer succinctly. Maybe you have to use it multiple times before answering."
#      )
# )
#
# result = agent.invoke({
#     'messages': [
#         {
#             'role': 'user',
#             'content': "What fruits does the person like?"
#         }
#     ],
# })
#
# print(result)
# print(result['messages'][-1].content)


# ==========================================
# ==========================================
# DYNAMIC PROMPTS
# ==========================================
# ==========================================

# @dataclass
# class Context:
#     user_role: str
#
# @dynamic_prompt
# def user_role_prompt(request: ModelRequest) -> str:
#     user_role = request.runtime.context.user_role
#
#     base_prompt = 'You are a helpful and very concise assistant.'
#
#     match user_role:
#         case 'expert':
#             return f'{base_prompt} Provide detail technical responses.'
#         case 'beginner':
#             return f'{base_prompt} Keep your explanation simple and basic.'
#         case 'child':
#             return f'{base_prompt} Explain everything as if you were literally talking to a five-year old.'
#         case _:
#             return base_prompt
#
# model = init_chat_model(model='gpt-4.1-mini', temperature=0.3)
# agent = create_agent(
#     model=model,
#     middleware=[user_role_prompt],
#     context_schema=Context,
# )
#
# response = agent.invoke(
#     {
#         'messages': [
#             { 'role': 'user', 'content': 'Explain PCA'}
#         ],
#     },
#     context=Context(user_role='expert'),
# )
#
# print(response)


# ==========================================
# ==========================================
# DYNAMIC MODELS
# ==========================================
# ==========================================

#
# basic_model = init_chat_model(model='gpt-4o-mini')
# advanced_model = init_chat_model(model='gpt-4.1-mini')
#
# @wrap_model_call
# def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
#     message_count = len(request.state['messages'])
#
#     if message_count > 3:
#         model = advanced_model
#     else:
#         model = basic_model
#
#     request.model = model
#
#     return handler(request)
#
# agent = create_agent(model=basic_model, middleware=[dynamic_model_selection])
#
# response = agent.invoke({
#     'messages': [
#         SystemMessage('You are a helpful assistant.'),
#         HumanMessage('What is 1 +1 ?'),
#     ]
# })
#
# print(response['messages'][-1].content)
# print(response['messages'][-1].response_metadata['model_name'])


# ==========================================
# ==========================================
# CUSTOM MIDDLEWARE
# ==========================================
# ==========================================

# class HooksDemo(AgentMiddleware):
#
#     def __init__(self):
#         super().__init__()
#         self.start_time = 0.0
#
#     def before_agent(self, state: AgentState, runtime):
#         self.start_time = time()
#         print('before agent triggered')
#
#     def after_agent(self, state: AgentState, runtime):
#         print('after agent triggered')
#     def before_model(self, state: AgentState, runtime):
#         print('before model triggered')
#     def after_model(self, state: AgentState, runtime):
#         print('after model triggered', time() - self.start_time)
# model = init_chat_model(model='gpt-4.1-mini', temperature=0.3)
# agent = create_agent(
#     model=model,
#     middleware=[HooksDemo()]
# )
#
# response = agent.invoke({
#     'messages': [
#         SystemMessage('You are a helpful assistant.'),
#         HumanMessage('What is NBA?'),
#     ]
# })
#
# print(response['messages'][-1].content)


# ==========================================
# ==========================================
# LANGCHAIN MIDDLEWARE
# ==========================================
# ==========================================
agent = create_agent(
    model="gpt-4o",
    middleware=[
        SummarizationMiddleware(
            model="gpt-4o-mini",
            trigger=("tokens", 4000),
            keep=("messages", 20),
        ),
    ],
)

response = agent.invoke({
    'messages': [
        SystemMessage('You are a helpful assistant.'),
        HumanMessage('What is NBA?'),
    ]
})

print(response['messages'][-1].content)
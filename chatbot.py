import os

from typing import Sequence
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.mongodb import MongoDBSaver
from typing_extensions import Annotated, TypedDict
from pymongo import MongoClient
from vector import vectors
import os



load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
client = MongoClient(MONGO_URL)

memory = MongoDBSaver(
    client=client,  
    db_name="dpu_care"
)

def main(model_name: str, system_template: str, text: str, thread_id: str, temperature: float = 0.7):
    """function main
    parameter:
        model name: str (require)
        temperature: float (optional)
        system_templete: str (require)
        text: str (require)
        thread_id: str (require)
        stream: bool (optional)"""
        
    llm = ChatOpenAI(model=model_name, temperature=temperature)

    config = {"configurable": {"thread_id": thread_id}}
    vector_store = vectors(directory="./vectorDB", collection_name="vector")

    class State(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]

    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
    prompt_template = ChatPromptTemplate.from_messages(
        [
            system_message_prompt,
            MessagesPlaceholder(variable_name="messages")
        ]
    )

    workflow = StateGraph(State)

    @tool
    def retrieve(query: str):
        "Retrieve information related to a query."

        retrieved_docs = vector_store.similarity_search_with_score(query=query, k=3)

        return retrieved_docs

    def query_or_respond(state: State):
        """Generate tool call for retrieval or respond."""
        
        llm_with_tool = llm.bind_tools([retrieve])
        prompt = prompt_template.invoke(state["messages"])
        
        response = llm_with_tool.invoke(prompt)
        
        return {"messages": [response]}


    tools = ToolNode([retrieve])

    workflow.add_node(query_or_respond)
    workflow.add_node(tools)

    workflow.set_entry_point("query_or_respond")
    workflow.add_conditional_edges(
        "query_or_respond",
        tools_condition,
        {END: END, "tools": "tools"},
    )
    workflow.add_edge("tools", "query_or_respond")

    app = workflow.compile(checkpointer=memory)
    
    response = app.invoke(
        {"messages": [{"role": "user", "content": text}]},
        config=config
    )
    
    return { 
            "response": response["messages"][-1].content,
            "total_tokens": response["messages"][-1].response_metadata["token_usage"]["total_tokens"]
            }
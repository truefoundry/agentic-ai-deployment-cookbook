#Import libraries
import os, uuid
import sqlite3
from typing import TypedDict, Annotated, Literal, List
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langgraph.graph import add_messages, StateGraph, END, MessagesState
from langgraph.types import Command, interrupt
from dotenv import load_dotenv

# Load environment variables (TAVILY_API_KEY, LLM_GATEWAY_URL, etc.). Override existing loaded environment variables, if this command is rerun
load_dotenv(override=True)

# --- Configuration ---
# 1. Update the LLM initialization for LangGraph with TrueFoundry
llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL_LANGCHAIN"),
    base_url=os.getenv("LLM_GATEWAY_URL"),
    api_key=os.getenv("TFY_API_KEY"),
)

# --- Tools Setup ---
# Tavily Search Tool for web research
tavily_tool = TavilySearch(max_results=5)
tools = [tavily_tool]

# --- 2. Shared Graph State ---
class ResearchState(MessagesState):
    """
    Represents the state of our multi-step research process.
    Content is passed between nodes via this state dictionary.
    """

    query: str
    search_context: Annotated[List[str], add_messages] #every time the model returns search results - CHANGED
    human_feedback: Annotated[List[str], add_messages] #every time there's a feedback - CHANGED
    final_report: str


# --- 3. Agent Functions (Nodes) ---
# --- 3. Agent Functions (Nodes) ---
def researcher_node(state: ResearchState) -> ResearchState:
    """
    NODE 1: Acts as the Researcher Agent.
    1. Uses Tavily to find web context based on the query.
    2. Uses the LLM to summarize and synthesize the raw search results.
    """
    print("--- Researcher Node: Gathering Context ---")
    query = state["query"]
    feedback = state["human_feedback"] if "human_feedback" in state else ["No Feedback yet"] ##Adding human feedback
    
    # 1. Tool Call: Tavily Search
    search_context = tavily_tool.invoke({"query": query})
    # Format the search results cleanly
    context_string = "\n\n".join(
        [f"Source: {r['url']}\nTitle: {r['title']}\nSnippet: {r['content'][:300]}..." for r in search_context["results"]]
    )

   # 2. LLM Call: Synthesize/Summarize
    researcher_persona = (
        "You are a Senior Web Researcher. Your goal is to gather the latest and most relevant "
        "information about the user's query and format it as a comprehensive summary. "
        "You are an expert at utilizing the Tavily web search tool to find real-time, accurate, "
        "and cited information on any given topic. Your output must be precise and well-structured."
    )
    
    researcher_instruction = (
        f"""
        TASK: Conduct an 'advanced' web search for the user's query: '{query}'. 

        Human Feedback: {feedback[-1] if feedback else "No feedback yet"}

        Focus on recent developments and list all sources used in the final summary. 
        
        Consider previous human feedback to refine the reponse.
        
        The final output MUST be a single, well-structured text summary of findings, 
        using ONLY the context provided below. Expected output: A comprehensive, cited summary.

        RESEARCH CONTEXT:
        ---
        {context_string}
        ---
        """
    )
    
    researcher_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=researcher_persona),
        HumanMessage(content=researcher_instruction)
    ])
    
    summary = researcher_prompt | llm
    summary_content = summary.invoke({}).content
    
    print(f"[researcher_node] Generated summary:\n{summary_content}\n")

    
    # Update the state with the synthesized context
    return {"search_context": [AIMessage(content=summary_content)]}

def human_node(state: ResearchState) -> ResearchState: 
    """Human Intervention node - loops back to model unless input is done"""

    print("--- Human Node: Awaiting Human Feedback ---")

    search_context = state["search_context"]

    # Interrupt to get user feedback

    user_feedback = interrupt(
        {
            "search_context": search_context, 
            "message": "Provide feedback or type 'done' to finish"
        }
    )

    print(f"[human_node] Received human feedback: {user_feedback}")

    # If user types "done", transition to END node
    if user_feedback.lower() == "done": 
        return Command(update={"human_feedback": state["human_feedback"] + ["Finalised"]}, goto="writer")

    # Otherwise, update feedback and return to model for re-generation
    return Command(update={"human_feedback": state["human_feedback"] + [user_feedback]}, goto="researcher")
    
def writer_node(state: ResearchState) -> ResearchState:
    """
    NODE 2: Acts as the Writer Agent.
    Takes the synthesis from the Researcher and formats it into a final Markdown report.
    """
    print("--- Writer Node: Generating Final Report ---")
    
    # Get the synthesized context from the previous node's output in the state
    summary = state.get("search_context", "No context found.")
    query = state["query"]

    # LLM Call: Writer
    writer_persona = (
        "You are a Professional Technical Writer. You are a meticulous technical writer "
        "who turns raw research data into polished, production-ready documentation. "
        "Your goal is to write a final, professionally formatted markdown report based on the context provided."
    )

    writer_instruction = (
        f"""
        TASK: Based on the summary provided by the Researcher Agent, write a final report for the query: '{query}'.
        
        The report must be in **Markdown format** with a clear title (using #) and bullet points.
        The final output must be ONLY the Markdown text. Expected output: A Markdown formatted report.

        RESEARCH SUMMARY:
        ---
        {summary}
        ---
        """
    )

    writer_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=writer_persona),
        HumanMessage(content=writer_instruction)
    ])

    report_chain = writer_prompt | llm
    final_report_content = report_chain.invoke({}).content
    
    # Update the state with the final report (this will be the final output of the graph)
    return {"final_report": final_report_content}


# # --- 4. Graph Construction ---
# # Initialize the StateGraph
# workflow = StateGraph(ResearchState)

# # Add nodes corresponding to the agents
# workflow.add_node("researcher", researcher_node)
# workflow.add_node("human", human_node)
# workflow.add_node("writer", writer_node)

# # Define the sequential edges (Researcher -> Writer -> END)
# workflow.set_entry_point("researcher")
# workflow.add_edge("researcher", "human")
# workflow.add_edge("human", "writer")
# workflow.set_finish_point("writer")

# # Compile the graph with database-backed memory
# app = workflow.compile()

# --- 4. Graph Construction for LangGraph Studio ---
app = (
    StateGraph(ResearchState)
    .add_node("researcher", researcher_node)
    .add_node("human", human_node)
    .add_node("writer", writer_node)
    .add_edge("__start__", "researcher")
    .add_edge("researcher", "human")
    .set_finish_point("writer")
    .compile(name="Human-in-the-Loop Graph")
)
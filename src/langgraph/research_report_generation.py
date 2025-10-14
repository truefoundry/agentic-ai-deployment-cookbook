#Import libraries
import os
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END, MessagesState
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
    search_results: str
    final_report: str

# --- 3. Agent Functions (Nodes) ---
def researcher_node(state: ResearchState) -> ResearchState:
    """
    NODE 1: Acts as the Researcher Agent.
    1. Uses Tavily to find web context based on the query.
    2. Uses the LLM to summarize and synthesize the raw search results.
    """
    print("--- Researcher Node: Gathering Context ---")
    query = state["query"]
    
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
        Focus on recent developments and list all sources used in the final summary.
        
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
    
    # Update the state with the synthesized context
    return {"search_context": summary_content}


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

# --- 4. Graph Construction ---
# Initialize the StateGraph
workflow = StateGraph(ResearchState)

# Add nodes corresponding to the agents
workflow.add_node("researcher", researcher_node)
workflow.add_node("writer", writer_node)

# Define the sequential edges (Researcher -> Writer -> END)
workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "writer")
workflow.set_finish_point("writer")

# Compile the graph
app = workflow.compile()

# --- Function to be Wrapped by FastMCP --- Make this asynchronous here. 
async def run_research_analysis(query: str) -> str:
    """
    Executes the compiled LangGraph workflow with a user query.
    This function is what the FastMCP server will call.
    """
    initial_state = {
        "query": query, 
        "search_context": "", 
        "final_report": "", 
        "messages": [HumanMessage(content=query)]
    }
    
    # Invoke the compiled graph
    final_state = await app.ainvoke(initial_state)
    
    # Return the final report content
    return final_state["final_report"]

if __name__ == "__main__":
    # Example Hackathon Query
    query = "Latest developments in quantum computing hardware in 2025" 
    print(f"--- Starting LangGraph Research Flow for: {query} ---")
    result = run_research_analysis(query)
    print("\n\n=== FINAL REPORT (LangGraph Output) ===")
    print(result)

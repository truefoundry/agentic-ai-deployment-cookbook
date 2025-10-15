# Import libraries
import os

from crewai import LLM, Agent, Crew, Process, Task
from crewai_tools import FileWriterTool, TavilySearchTool
from dotenv import load_dotenv

# Load environment variables (TAVILY_API_KEY, LLM_GATEWAY_URL, etc.). Override existing loaded environment variables, if this command is rerun
load_dotenv(override=True)

# --- Configuration ---
# 1. Update the LLM initialization for CrewAI with TrueFoundry
llm = LLM(
    model=os.getenv("LLM_MODEL_CREWAI"),
    base_url=os.getenv("LLM_GATEWAY_URL"),
    api_key=os.getenv("TFY_API_KEY"),
)

# --- Tools Setup ---
# Tavily Search Tool for web research
tavily_search_tool = TavilySearchTool()

# File Writer Tool for saving the final report
file_writer_tool = FileWriterTool()

# --- 2. Agents Definition ---
# 1) Researcher Agent (Uses TavilySearchTool)
researcher_agent = Agent(
    role="Senior Web Researcher",
    goal="Gather the latest and most relevant information about the user's query and format it as a comprehensive summary.",
    backstory="""You are an expert at utilizing the Tavily web search tool to find real-time, accurate,
                 and cited information on any given topic. Your output is precise and well-structured.""",
    tools=[tavily_search_tool],
    llm=llm,
    verbose=True,
    memory=False,
    allow_delegation=False,
)

# 2) Report Agent (Uses FileWriterTool)
report_agent = Agent(
    role="Professional Technical Writer",
    goal="Write a final, professionally formatted markdown report based on the context provided by the Researcher Agent",
    backstory="""You are a meticulous technical writer who turns raw research data into polished,
                 production-ready documentation.""",
    tools=[],
    llm=llm,
    verbose=True,
)

# --- 3. Tasks Definition ---
# 1) Researcher Agent Task
research_task = Task(
    description="""Conduct an 'advanced' web search for the user's query: '{query}'.
                   Focus on recent developments (past 6 months) and list all sources.
                   The final output must be a single, well-structured text summary of findings.""",
    expected_output="A comprehensive, cited summary of the research topic.",
    agent=researcher_agent,
)

# 2) Report Agent Task
report_task = Task(
    description="""Based on the summary provided by the Researcher Agent, write a final report.
                   The report must be in **Markdown format** with a title and bullet points.""",
    expected_output="A Markdown formatted report with a title and bullet points.",
    agent=report_agent,
    context=[research_task],  # Task waits for research to complete
)

# --- Crew Initialization ---
research_crew = Crew(
    agents=[researcher_agent, report_agent],
    tasks=[research_task, report_task],
    process=Process.sequential,
    verbose=True,  # Higher verbosity for clear demonstration
)


# --- Function to be Wrapped by FastMCP --- Make this asynchronous here.
async def run_agent(query: str):
    """Executes the two-agent research crew."""
    print(f"--- Starting Crew for query: {query} ---")

    # Pass the user query to the crew's initial task
    result = await research_crew.kickoff_async(inputs={"query": query})

    # Return the final output message from the Report Agent
    return result.raw


if __name__ == "__main__":
    # Example Hackathon Query
    query = "Latest developments in quantum computing hardware in 2025"

    final_output = run_agent(query)

    print("\n\n--- Final Result from Crew ---")
    print(final_output)

"""
Research Report Generator MCP Server - Provides real-time research tool 
via Model Context Protocol (MCP) using a simplified multi-agent backend.
"""

#Imports
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse
from src.crewai.research_report_generation import run_research_analysis

# --- 1. FastMCP Initialization and Configuration ---
# Initialize the server. Authentication logic can be added here if desired.
mcp = FastMCP("research_report_generation", stateless_http=True) #stateless_http is required for StreamableHTTP communication

# --- 2. Defining Tools (The Core) ---
@mcp.tool()
async def conduct_research_and_report(query: str) -> str:
    """
    Executes a two-agent workflow to perform real-time web research (via Tavily), 
    and generate a detailed report in a Markdown format.
    
    This is the complete research-to-delivery action.

    Args:
        query (str): The research topic (e.g., "Latest developments in quantum computing hardware").
        
    Returns:
        str: The full content of the generated report, or a detailed error message.
    """
    try:
        # Call the execution function. 
        # run_research_analysis() returns the FINAL report content as a string.
        report_content = await run_research_analysis(query)
        
        # The report agent handles the file save internally, so we just return the content.
        return f"Successfully completed research and formatted report.\n\n--- Report Content ---\n{report_content}"
        
    except Exception as e:
        # Provide a detailed error message to the calling LLM agent
        return f"Tool Execution Error: Could not complete the workflow. Details: {e}"
    

# --- 3. Defining Resources (Server Context) ---
@mcp.resource("config://server-info")
def get_server_info() -> dict:
    """Provides configuration details about this MCP server and its capabilities."""
    return {
        "server_name": mcp.name,
        "description": "Exposes the research and report generation agent.",
        "tool_flow": "TavilySearch -> LLM Summary -> FileWriteTool",
        "output_file": "research_report.md"
    }

# --- 4. Custom Routes (Health Check) ---
@mcp.custom_route("/health", methods=["GET"])
def health_check(request: Request) -> JSONResponse:
    """Standard health check endpoint for monitoring server status."""
    return JSONResponse({"status": "OK", "name": mcp.name})

# --- 5. Run the Server ---
if __name__ == "__main__":
    # Standard settings for deployment in a container environment like TrueFoundry
    mcp.settings.host = "0.0.0.0" 
    mcp.settings.port = 8000 
    
    print(f"Starting FastMCP Server '{mcp.name}' on http://{mcp.settings.host}:{mcp.settings.port}/mcp")
    mcp.run(transport="streamable-http")

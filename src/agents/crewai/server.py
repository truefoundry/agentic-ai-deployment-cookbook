"""FastAPI backend for Research Report Generation."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse

# Import the new run_agent function
from src.agents.crewai.agent import run_agent

app = FastAPI(
    title="CrewAI - Research Report Generation Agent",
    root_path=os.getenv("TFY_SERVICE_ROOT_PATH", ""),
    docs_url="/",
)

# CORS middleware for local development/different origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Define Health Check endpoint
@app.get("/health")
def status(request: Request) -> JSONResponse:
    """Standard health check endpoint for monitoring service status."""
    return JSONResponse({"status": "OK"})


# Add a Pydantic Model to ensure input types
class UserInput(BaseModel):
    """Request model for user input to the agent."""

    user_input: str


# Primary FastAPI endpoint
@app.post("/chat")
async def run_agent_endpoint(user_input: UserInput):
    """
    Receives user input and executes the agent to provide a response.
    """
    return await run_agent(user_input.user_input)

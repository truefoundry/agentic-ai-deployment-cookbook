"""
News Processing MCP Server - Provides tools for news processing via Model Context Protocol (MCP).

This server exposes tools for converting news articles to bullet points and other text processing tasks.
"""

import re

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

# --- 1. FastMCP Initialization and Configuration ---
mcp = FastMCP("news_processing_service", stateless_http=True)


# --- 2. Defining Tools ---
@mcp.tool()
def convert_to_bullet_points(text: str, max_points: int = 10) -> str:
    """
    Converts a block of text into well-formatted bullet points.

    Args:
        text (str): The raw text content to convert to bullet points.
        max_points (int): Maximum number of bullet points to generate (default: 10).

    Returns:
        str: Formatted bullet points with proper markdown formatting.
    """
    try:
        if not text or not text.strip():
            return "No content provided to convert to bullet points."

        # Clean and split the text into sentences
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 20]

        if not sentences:
            return "• Unable to extract meaningful content for bullet points."

        # Limit the number of points
        sentences = sentences[:max_points]

        # Create bullet points
        bullet_points = []
        for i, sentence in enumerate(sentences, 1):
            # Clean up the sentence
            sentence = sentence.replace("\n", " ").replace("\r", " ")
            sentence = re.sub(r"\s+", " ", sentence).strip()

            if sentence:
                bullet_points.append(f"• {sentence}")

        if not bullet_points:
            return "• No valid content found to convert to bullet points."

        return "\n".join(bullet_points)

    except Exception as e:
        return f"Error converting to bullet points: {str(e)}"


@mcp.tool()
def summarize_news_article(article_text: str, summary_length: str = "medium") -> str:
    """
    Creates a concise summary of a news article.

    Args:
        article_text (str): The full text of the news article.
        summary_length (str): Length of summary - "short", "medium", or "long" (default: "medium").

    Returns:
        str: A concise summary of the article.
    """
    try:
        if not article_text or not article_text.strip():
            return "No article content provided for summarization."

        # Simple extractive summarization by taking first few sentences
        sentences = re.split(r"[.!?]+", article_text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 15]

        if not sentences:
            return "Unable to extract meaningful content for summarization."

        # Determine number of sentences based on summary length
        length_map = {"short": 2, "medium": 4, "long": 6}
        num_sentences = length_map.get(summary_length, 4)

        # Take the first N sentences as summary
        summary_sentences = sentences[:num_sentences]
        summary = ". ".join(summary_sentences)

        if summary and not summary.endswith("."):
            summary += "."

        return summary

    except Exception as e:
        return f"Error summarizing article: {str(e)}"


@mcp.tool()
def extract_key_facts(text: str) -> str:
    """
    Extracts key facts and important information from text.

    Args:
        text (str): The text content to extract facts from.

    Returns:
        str: Key facts formatted as a list.
    """
    try:
        if not text or not text.strip():
            return "No content provided to extract facts from."

        # Look for patterns that indicate facts (numbers, dates, names, etc.)
        facts = []

        # Extract dates
        date_pattern = r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}\b"
        dates = re.findall(date_pattern, text)
        if dates:
            facts.append(f"• Dates mentioned: {', '.join(set(dates))}")

        # Extract numbers that might be statistics
        number_pattern = r"\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:percent|%|million|billion|thousand|dollars?|\$)\b"
        numbers = re.findall(number_pattern, text, re.IGNORECASE)
        if numbers:
            facts.append(f"• Key statistics: {', '.join(set(numbers))}")

        # Extract quoted statements
        quote_pattern = r'"([^"]+)"'
        quotes = re.findall(quote_pattern, text)
        if quotes:
            facts.append(f"• Notable quotes: {quotes[0]}")  # Take first quote

        if not facts:
            # Fallback: extract first few sentences as key points
            sentences = re.split(r"[.!?]+", text)
            sentences = [
                s.strip() for s in sentences if s.strip() and len(s.strip()) > 20
            ]
            if sentences:
                facts = [f"• {sentence}" for sentence in sentences[:3]]

        return (
            "\n".join(facts)
            if facts
            else "• No specific facts could be extracted from the content."
        )

    except Exception as e:
        return f"Error extracting facts: {str(e)}"


# --- 3. Defining Resources (Server Info) ---
@mcp.resource("config://server-info")
def get_server_info() -> dict:
    """
    Provides information about the MCP server and its capabilities.
    """
    return {
        "server_name": mcp.name,
        "description": "A news processing MCP server with text processing tools.",
        "tools": [
            "convert_to_bullet_points(text, max_points) -> formatted bullet points",
            "summarize_news_article(article_text, summary_length) -> article summary",
            "extract_key_facts(text) -> key facts and statistics",
        ],
    }


# --- 4. Custom Routes (Health Check) ---
@mcp.custom_route("/health", methods=["GET"])
def health_check(request: Request) -> JSONResponse:
    """Basic liveness probe endpoint for container monitoring."""
    return JSONResponse({"status": "OK", "name": mcp.name})


# --- 5. Run the Server ---
if __name__ == "__main__":
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = 8000
    print(
        f"Starting Simple FastMCP Server '{mcp.name}' on http://{mcp.settings.host}:{mcp.settings.port}/mcp"
    )
    mcp.run(transport="streamable-http")

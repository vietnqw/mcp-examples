from mcp.server.fastmcp import FastMCP
from tools.weather_tools import register_tools

def create_app() -> FastMCP:
    """Create and configure the MCP application."""
    # Initialize FastMCP server
    mcp = FastMCP("weather")
    
    # Register all tools
    register_tools(mcp)
    
    return mcp

if __name__ == "__main__":
    # Initialize and run the server
    app = create_app()
    app.run(transport='stdio')
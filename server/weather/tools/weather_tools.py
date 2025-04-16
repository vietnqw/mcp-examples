from mcp.server.fastmcp import FastMCP
from services.weather_service import get_state_alerts, get_location_forecast  # Absolute import


def register_tools(mcp_server: FastMCP) -> None:
    """Register all weather tools with the MCP server."""
    
    @mcp_server.tool()
    async def get_alerts(state: str) -> str:
        """Get weather alerts for a US state.

        Args:
            state: Two-letter US state code (e.g. CA, NY)
        """
        return await get_state_alerts(state)

    @mcp_server.tool()
    async def get_forecast(latitude: float, longitude: float) -> str:
        """Get weather forecast for a location.

        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
        """
        return await get_location_forecast(latitude, longitude)

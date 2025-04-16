import asyncio
import os
import json
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = os.getenv("GEMINI_MODEL")
        self.server_path = os.getenv("MCP_SERVER_PATH")

    async def connect_to_server(self):
        """Connect to an MCP server """

        server_params = StdioServerParameters(
            command="uv",
            args=[
                "--directory",
                self.server_path,
                "run",
                "main.py"
            ],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Gemini and available tools"""
        final_text = []
        
        # Get available tools
        mcp_tools = await self.session.list_tools()
        
        # Format tools for Gemini
        tools = [
            types.Tool(
                function_declarations=[
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": {
                            k: v
                            for k, v in tool.inputSchema.items()
                            if k not in ["additionalProperties", "$schema"]
                        },
                    }
                ]
            )
            for tool in mcp_tools.tools
        ]
        
        # Make request to Gemini
        response = self.client.models.generate_content(
            model=self.model,
            contents=query,
            config=types.GenerateContentConfig(
                temperature=0,
                tools=tools,
            ),
        )
        
        # Add model's text response if available
        if response.text:
            final_text.append(response.text)
        
        # Handle function call if present
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                    tool_name = function_call.name
                    tool_args = dict(function_call.args)
                    
                    # Execute tool call
                    final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                    result = await self.session.call_tool(tool_name, tool_args)
                    
                    # Format and add the result
                    try:
                        result_text = result.content
                        final_text.append(f"Tool result: {result_text}")
                        
                        # Make a simplified follow-up request with just the tool result
                        follow_up_prompt = f"""Original query: {query}
                        
Tool used: {tool_name} with parameters {tool_args}
                        
Tool result: {result_text}
                        
Please provide a human-friendly summary of this weather information."""
                        
                        follow_up = self.client.models.generate_content(
                            model=self.model,
                            contents=follow_up_prompt,
                        )
                        
                        if follow_up.text:
                            final_text.append(follow_up.text)
                    except Exception as e:
                        final_text.append(f"Error processing tool result: {str(e)}")
        
        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    client = MCPClient()
    try:
        await client.connect_to_server()
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
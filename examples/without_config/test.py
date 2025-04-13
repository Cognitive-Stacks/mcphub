from mcphub import MCPHub
import json

async def main():

    hub = MCPHub()
    
    async with hub.fetch_openai_mcp_server(
        mcp_name="MCP-Mirror/Automata-Labs-team_MCP-Server-Playwright",
        cache_tools_list=True
    ) as server:
        # Step 3: List available tools from the MCP server
        # This shows what capabilities are available to your agent
        tools = await server.list_tools()
        
        # Pretty print the tools for better readability
        tools_dict = [
            dict(tool) if hasattr(tool, "__dict__") else tool for tool in tools
        ]
        print("Available MCP Tools:")
        print(json.dumps(tools_dict, indent=2))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
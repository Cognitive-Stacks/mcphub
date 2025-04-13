from mcphub import MCPHub

server_name = "Gloomysunday28/mcp-server"

async def framework_examples():
    hub = MCPHub()
    
    # 1. OpenAI Agents Integration
    async with hub.fetch_openai_mcp_server(
        mcp_name=server_name,
        cache_tools_list=True
    ) as server:
        tools = await server.list_tools()
        print(f"Tools from MCP server: {tools}")
    # 2. LangChain Tools Integration
    langchain_tools = await hub.fetch_langchain_mcp_tools(
        mcp_name=server_name,
        cache_tools_list=True
    )
    
    print(f"LangChain tools from MCP server: {langchain_tools}")
    
    # 3. Autogen Adapters Integration
    autogen_adapters = await hub.fetch_autogen_mcp_adapters(
        mcp_name=server_name
    )
    # Use adapters with Autogen

    print(f"Autogen adapters from MCP server: {autogen_adapters}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(framework_examples())
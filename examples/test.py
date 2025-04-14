import asyncio
import json
from agents import Agent, Runner
from mcphub import MCPHub

async def main():
    """
    Example of using MCPHub to integrate MCP servers with OpenAI Agents.
    
    This example demonstrates:
    1. Initializing MCPHub
    2. Fetching and using an MCP server
    3. Listing available tools
    4. Creating and running an agent with MCP tools
    """
    
    # Step 1: Initialize MCPHub
    # MCPHub will automatically:
    # - Find .mcphub.json in your project
    # - Load server configurations
    # - Set up servers (clone repos, run setup scripts if needed)
    hub = MCPHub()
    
    # Step 2: Create an MCP server instance using async context manager
    # Parameters:
    # - mcp_name: The name of the server from your .mcphub.json
    # - cache_tools_list: Cache the tools list for better performance
    async with hub.fetch_openai_mcp_server(
        mcp_name="sequential-thinking-mcp",
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

        # Step 4: Create an OpenAI Agent with MCP server
        # The agent can now use all tools provided by the MCP server
        agent = Agent(
            name="Assistant",
            instructions="Use the available tools to accomplish the given task",
            mcp_servers=[server]  # Provide the MCP server to the agent
        )
        
        # Step 5: Run your agent with a complex task
        # The agent will automatically have access to all MCP tools
        complex_task = """Please help me analyze the following complex problem: 
                      We need to design a new feature for our product that balances user privacy 
                      with data collection for improving the service. Consider the ethical implications, 
                      technical feasibility, and business impact. Break down your thinking process 
                      step by step, and provide a detailed recommendation with clear justification 
                      for each decision point."""
        
        # Execute the task and get the result
        result = await Runner.run(agent, complex_task)
        print("\nAgent Response:")
        print(result)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
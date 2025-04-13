from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from agents.mcp import MCPServerStdio
from autogen_ext.tools.mcp import StdioMcpToolAdapter
from langchain_core.tools import BaseTool
from mcp import StdioServerParameters
from .mcp_servers import MCPServerConfig, MCPServers, MCPServersParams


@dataclass
class MCPHub:
    servers_params: MCPServersParams = field(init=False)

    def __post_init__(self):
        config_path = self._find_config_path()
        self.servers_params = MCPServersParams(config_path)
        self.servers = MCPServers(self.servers_params)

    def _find_config_path(self) -> Optional[str]:
        current_dir = Path.cwd()
        for parent in [current_dir] + list(current_dir.parents):
            config_path = parent / ".mcphub.json"
            if config_path.exists():
                return str(config_path)
        # Instead of raising an error, return None to indicate no config file was found
        # This will allow us to still use preconfigured servers
        return None

    def fetch_server_params(self, mcp_name: str) -> Optional[MCPServerConfig]:
        return self.servers_params.retrieve_server_params(mcp_name)
    
    def fetch_stdio_server_config(self, mcp_name: str) -> Optional[StdioServerParameters]:
        return self.servers_params.convert_to_stdio_params(mcp_name)
    
    def fetch_openai_mcp_server(self, mcp_name: str, cache_tools_list: bool = True) -> MCPServerStdio:
        """
        Fetch and return an OpenAI MCP server instance.
        
        Args:
            mcp_name: The name of the MCP server to fetch
            cache_tools_list: Whether to cache the tools list
            
        Returns:
            MCPServerStdio: The configured MCP server
        """
        return self.servers.make_openai_mcp_server(mcp_name, cache_tools_list)
    
    async def fetch_langchain_mcp_tools(self, mcp_name: str, cache_tools_list: bool = True) -> List[BaseTool]:
        """
        Fetch and return a list of Langchain MCP tools.
        
        Args:
            mcp_name: The name of the MCP server to fetch
            cache_tools_list: Whether to cache the tools list
            
        Returns:
            List[BaseTool]: A list of Langchain MCP tools
        """
        return await self.servers.get_langchain_mcp_tools(mcp_name, cache_tools_list)
    
    async def fetch_autogen_mcp_adapters(self, mcp_name: str) -> List[StdioMcpToolAdapter]:
        """
        Fetch and return an Autogen MCP adapter.
        
        Args:
            mcp_name: The name of the MCP server to fetch
            
        Returns:
            StdioMcpToolAdapter: The configured MCP adapter
        """
        return await self.servers.make_autogen_mcp_adapters(mcp_name)
    
    async def list_tools(self, mcp_name: str) -> List[BaseTool]:
        """
        List all tools from an MCP server.
        
        Args:
            mcp_name: The name of the MCP server configuration to use

        Returns:
            List[BaseTool]: List of tools provided by the MCP server
        """
        return await self.servers.list_tools(mcp_name)
import pytest
from unittest import mock
from pathlib import Path

from mcphub.mcphub import MCPHub
from mcphub.mcp_servers import MCPServerConfig
from mcphub.mcp_servers.exceptions import ServerConfigNotFoundError


class TestMCPHub:
    @mock.patch('pathlib.Path.cwd')
    @mock.patch('pathlib.Path.exists')
    def test_find_config_path_success(self, mock_exists, mock_cwd, temp_config_file):
        """Test successfully finding config path."""
        # Mock cwd and exists to find the config file
        mock_cwd.return_value = Path(temp_config_file).parent
        mock_exists.return_value = True
        
        # Initialize MCPHub which will call _find_config_path
        hub = MCPHub()
        
        # Test that server_params was initialized correctly
        assert hub.servers_params is not None
    
    @mock.patch('pathlib.Path.cwd')
    @mock.patch('pathlib.Path.exists')
    def test_find_config_path_failure(self, mock_exists, mock_cwd):
        """Test failure to find config path."""
        # Mock cwd and exists to not find the config file
        mock_cwd.return_value = Path("/some/path")
        mock_exists.return_value = False
        
        # Initializing MCPHub should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            hub = MCPHub()
    
    def test_fetch_server_params(self, mock_mcphub_init, temp_config_file):
        """Test fetching server parameters."""
        hub = MCPHub()
        
        # Create a mock for retrieve_server_params to return expected values
        server_config = MCPServerConfig(
            package_name="test-mcp-server",
            command="python",
            args=["-m", "test_server"],
            env={"TEST_ENV": "test_value"},
            description="Test MCP Server",
            tags=["test", "demo"]
        )
        
        # Mock the retrieve_server_params method
        hub.servers_params.retrieve_server_params = mock.MagicMock(
            side_effect=lambda name: server_config if name == "test-server" else None
        )
        
        # Test retrieving server parameters
        result = hub.fetch_server_params("test-server")
        assert result is not None
        assert result.package_name == "test-mcp-server"
        
        # Test with non-existent server
        assert hub.fetch_server_params("non-existent") is None
    
    def test_fetch_stdio_server_config(self, mock_mcphub_init, temp_config_file):
        """Test fetching StdioServerParameters."""
        hub = MCPHub()
        
        # Create a mock StdioServerParameters
        from mcp import StdioServerParameters
        stdio_params = StdioServerParameters(
            command="python",
            args=["-m", "test_server"],
            env={"TEST_ENV": "test_value"}
        )
        
        # Mock the convert_to_stdio_params method
        hub.servers_params.convert_to_stdio_params = mock.MagicMock(
            side_effect=lambda name: stdio_params if name == "test-server" else None
        )
        
        # Test retrieving stdio server parameters
        result = hub.fetch_stdio_server_config("test-server")
        assert result is not None
        assert result.command == "python"
        assert result.args == ["-m", "test_server"]
        
        # Set up the method to raise an exception for non-existent server
        hub.servers_params.convert_to_stdio_params.side_effect = lambda name: (
            stdio_params if name == "test-server" else (_ for _ in ()).throw(ServerConfigNotFoundError(f"Server '{name}' not found"))
        )
        
        # Test with non-existent server
        with pytest.raises(ServerConfigNotFoundError):
            hub.fetch_stdio_server_config("non-existent")
    
    @mock.patch('mcphub.mcp_servers.MCPServers.make_openai_mcp_server')
    def test_fetch_openai_mcp_server(self, mock_make_server, mock_mcphub_init, temp_config_file):
        """Test fetching an OpenAI MCP server."""
        mock_server = mock.MagicMock()
        mock_make_server.return_value = mock_server
        
        hub = MCPHub()
        server = hub.fetch_openai_mcp_server("test-server")
        
        assert server == mock_server
        mock_make_server.assert_called_once_with("test-server", True)
    
    @mock.patch('mcphub.mcp_servers.MCPServers.get_langchain_mcp_tools')
    async def test_fetch_langchain_mcp_tools(self, mock_get_tools, mock_mcphub_init, temp_config_file):
        """Test fetching Langchain MCP tools."""
        mock_tools = ["tool1", "tool2"]
        mock_get_tools.return_value = mock_tools
        
        hub = MCPHub()
        tools = await hub.fetch_langchain_mcp_tools("test-server")
        
        assert tools == mock_tools
        mock_get_tools.assert_called_once_with("test-server", True)
    
    @mock.patch('mcphub.mcp_servers.MCPServers.make_autogen_mcp_adapters')
    async def test_fetch_autogen_mcp_adapters(self, mock_make_adapters, mock_mcphub_init, temp_config_file):
        """Test fetching Autogen MCP adapters."""
        mock_adapters = ["adapter1", "adapter2"]
        mock_make_adapters.return_value = mock_adapters
        
        hub = MCPHub()
        adapters = await hub.fetch_autogen_mcp_adapters("test-server")
        
        assert adapters == mock_adapters
        mock_make_adapters.assert_called_once_with("test-server")
    
    @mock.patch('mcphub.mcp_servers.MCPServers.list_tools')
    async def test_list_tools(self, mock_list_tools, mock_mcphub_init, temp_config_file):
        """Test listing tools from an MCP server."""
        mock_tools = ["tool1", "tool2"]
        mock_list_tools.return_value = mock_tools
        
        hub = MCPHub()
        tools = await hub.list_tools("test-server")
        
        assert tools == mock_tools
        mock_list_tools.assert_called_once_with("test-server")
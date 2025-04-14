from unittest import mock
import pytest
from mcphub.mcp_servers import MCPServersParams
from mcphub.adapters.base import MCPBaseAdapter
from mcphub.mcp_servers.exceptions import ServerConfigNotFoundError

class TestAdapter(MCPBaseAdapter):
    """Test implementation of base adapter"""
    pass

async def test_base_adapter_get_server_config(test_config_path):
    """Test getting server configuration."""
    params = MCPServersParams(str(test_config_path))
    adapter = TestAdapter(params)
    
    config = adapter.get_server_config("test-mcp")
    assert config.package_name == "test-package"
    assert config.command == "echo"
    
    with pytest.raises(ServerConfigNotFoundError):
        adapter.get_server_config("non-existent")

async def test_base_adapter_get_server_params(test_config_path):
    """Test getting server parameters."""
    params = MCPServersParams(str(test_config_path))
    adapter = TestAdapter(params)
    
    server_params = adapter.get_server_params("test-mcp")
    assert server_params.command == "echo"
    assert server_params.args == ["test"]
    assert server_params.env == {"TEST_ENV": "test_value"}

@pytest.mark.asyncio
@mock.patch('mcphub.adapters.base.MCPBaseAdapter.get_tools')
async def test_base_adapter_get_tools(mock_get_tools, test_config_path):
    """Test getting tools from base adapter."""
    # Setup
    params = MCPServersParams(str(test_config_path))
    adapter = TestAdapter(params)
    
    # Setup mock tools
    mock_tools = [
        mock.Mock(name="tool1", description="test tool 1"),
        mock.Mock(name="tool2", description="test tool 2")
    ]
    mock_get_tools.return_value = mock_tools
    
    # Execute
    tools = await adapter.get_tools("test-mcp")
    
    # Verify
    assert tools is mock_tools
    mock_get_tools.assert_called_once_with("test-mcp") 
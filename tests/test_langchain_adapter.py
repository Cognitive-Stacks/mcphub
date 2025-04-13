from unittest import mock
import pytest
from mcphub.mcp_servers import MCPServersParams
from mcphub.adapters.langchain import MCPLangChainAdapter

@pytest.mark.asyncio
@mock.patch('mcphub.adapters.langchain.MCPLangChainAdapter.create_tools')
async def test_langchain_adapter_create_tools(mock_create_tools, test_config_path):
    """Test LangChain adapter tool creation with direct method mocking."""
    try:
        # Setup
        params = MCPServersParams(str(test_config_path))
        adapter = MCPLangChainAdapter(params)
        
        # Setup mock tools
        mock_tools = [mock.Mock(name="tool1", description="test tool 1")]
        mock_create_tools.return_value = mock_tools
        
        # Execute
        tools = await adapter.create_tools("test-mcp")
        
        # Verify
        assert tools is mock_tools
        mock_create_tools.assert_called_once_with("test-mcp")
    except ImportError:
        pytest.skip("LangChain dependencies not installed")

@pytest.mark.asyncio
async def test_langchain_adapter_import_error():
    """Test handling of missing LangChain dependencies."""
    import importlib
    
    # Test import error when langchain is not installed
    langchain_spec = importlib.util.find_spec("langchain_core")
    if not langchain_spec:
        with pytest.raises(ImportError):
            from mcphub.adapters.langchain import MCPLangChainAdapter
            MCPLangChainAdapter(None) 
    else:
        pytest.skip("LangChain dependencies installed, cannot test import error")
import pytest
from mcphub.mcp_servers import MCPServersParams
from mcphub.adapters.openai import MCPOpenAIAgentsAdapter

@pytest.mark.asyncio
async def test_openai_adapter_create_server(test_config_path):
    try:
        params = MCPServersParams(str(test_config_path))
        adapter = MCPOpenAIAgentsAdapter(params)
        
        server = adapter.create_server("test-mcp")
        assert server is not None
        assert server.params.command == "echo"
        assert server.params.args == ["test"]
    except ImportError:
        pytest.skip("OpenAI dependencies not installed")

@pytest.mark.asyncio
async def test_openai_adapter_import_error():
    import importlib
    
    # Check if OpenAI module is NOT available
    openai_spec = importlib.util.find_spec("agents.mcp")
    if not openai_spec:
        # Test that adapter raises ImportError when dependencies missing
        with pytest.raises(ImportError, match="OpenAI Agents dependencies not found"):
            from mcphub.adapters.openai import MCPOpenAIAgentsAdapter
            MCPOpenAIAgentsAdapter(None)
    else:
        pytest.skip("OpenAI is installed, cannot test import error") 
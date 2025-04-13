from unittest import mock

import pytest

from mcphub.adapters.autogen import MCPAutogenAdapter
from mcphub.mcp_servers import MCPServersParams


@pytest.mark.asyncio
@mock.patch('mcphub.adapters.autogen.MCPAutogenAdapter.create_adapters')  # Mock the method directly
async def test_autogen_adapter_create_adapters(mock_create_adapters, test_config_path):
    """Test Autogen adapter creation with direct method mocking."""
    try:
        # Setup
        params = MCPServersParams(str(test_config_path))
        adapter = MCPAutogenAdapter(params)
        
        # Setup mock adapters
        mock_adapter_instance = mock.Mock(name='mock_autogen_adapter')
        mock_create_adapters.return_value = mock_adapter_instance
        
        # Execute
        adapters = await adapter.create_adapters("test-mcp")
        
        # Verify
        assert adapters is mock_adapter_instance  # Use identity comparison
        mock_create_adapters.assert_called_once_with("test-mcp")
    except ImportError:
        pytest.skip("Autogen dependencies not installed")

@pytest.mark.asyncio
async def test_autogen_adapter_import_error():
    import importlib

    # Test import error when autogen is not installed
    autogen_spec = importlib.util.find_spec("autogen_ext")
    if not autogen_spec:
        with pytest.raises(ImportError):
            from mcphub.adapters.autogen import MCPAutogenAdapter
            MCPAutogenAdapter(None)
    else:
        pytest.skip("Autogen dependencies installed, cannot test import error")
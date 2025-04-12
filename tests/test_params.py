import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from mcphub.mcp_servers.params import MCPServersParams, MCPServerConfig
from mcphub.mcp_servers.exceptions import ServerConfigNotFoundError


class TestMCPServersParams:
    def test_load_user_config(self, temp_config_file):
        """Test loading user configuration from a file."""
        params = MCPServersParams(str(temp_config_file))
        server_params = params.servers_params
        
        assert len(server_params) == 1
        assert server_params[0].package_name == "test-mcp-server"
        assert server_params[0].command == "python"
        assert server_params[0].args == ["-m", "test_server"]
        assert server_params[0].env == {"TEST_ENV": "test_value"}
        assert server_params[0].description == "Test MCP Server"
        assert server_params[0].tags == ["test", "demo"]
    
    def test_retrieve_server_params(self, temp_config_file):
        """Test retrieving server parameters by name."""
        params = MCPServersParams(str(temp_config_file))
        server_config = params.retrieve_server_params("test-server")
        
        assert server_config is not None
        assert server_config.package_name == "test-mcp-server"
        assert server_config.command == "python"
        
        # Test with non-existent server
        assert params.retrieve_server_params("non-existent") is None
    
    def test_convert_to_stdio_params(self, temp_config_file):
        """Test converting server parameters to StdioServerParameters."""
        params = MCPServersParams(str(temp_config_file))
        stdio_params = params.convert_to_stdio_params("test-server")
        
        assert stdio_params.command == "python"
        assert stdio_params.args == ["-m", "test_server"]
        assert stdio_params.env == {"TEST_ENV": "test_value"}
        
        # Test with non-existent server
        with pytest.raises(ServerConfigNotFoundError):
            params.convert_to_stdio_params("non-existent")
    
    def test_update_server_path(self, temp_config_file):
        """Test updating server path."""
        params = MCPServersParams(str(temp_config_file))
        params.update_server_path("test-server", "/new/path")
        
        server_config = params.retrieve_server_params("test-server")
        assert server_config.cwd == "/new/path"
        
        # Test with non-existent server
        with pytest.raises(ServerConfigNotFoundError):
            params.update_server_path("non-existent", "/new/path")
    
    def test_file_not_found(self):
        """Test handling of non-existent config file."""
        with pytest.raises(FileNotFoundError):
            MCPServersParams("/nonexistent/path/.mcphub.json")
    
    def test_invalid_json(self, tmp_path):
        """Test handling of invalid JSON in config file."""
        invalid_json_file = tmp_path / ".mcphub.json"
        with open(invalid_json_file, "w") as f:
            f.write("{ invalid json")
        
        with pytest.raises(ValueError):
            MCPServersParams(str(invalid_json_file))
    
    @patch('pathlib.Path.exists')
    def test_load_predefined_servers(self, mock_exists, mock_mcp_preconfigured_servers):
        """Test loading predefined server parameters."""
        # Create a config that references a predefined server
        config_content = {
            "mcpServers": {
                "my-server": {
                    "package_name": "predefined-server"
                }
            }
        }
        
        config_file = Path(mock_mcp_preconfigured_servers).parent / ".mcphub.json"
        with open(config_file, "w") as f:
            json.dump(config_content, f)
        
        # Setup mock for Path.exists()
        mock_exists.return_value = True
        
        # Mock _load_predefined_servers_params to return our test data
        mock_predefined_data = {
            "predefined-server": {
                "command": "python",
                "args": ["-m", "predefined_server"],
                "description": "Predefined MCP Server",
                "tags": ["predefined", "demo"]
            }
        }
        
        with patch.object(MCPServersParams, '_load_predefined_servers_params', return_value=mock_predefined_data):
            params = MCPServersParams(str(config_file))
            server_params = params.servers_params
            
            assert len(server_params) == 1
            assert server_params[0].package_name == "predefined-server"
            assert server_params[0].command == "python"
            assert server_params[0].args == ["-m", "predefined_server"]
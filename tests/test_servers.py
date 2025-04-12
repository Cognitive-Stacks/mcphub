import json
import pytest
import subprocess
from pathlib import Path
from unittest import mock

from mcphub.mcp_servers.servers import MCPServers
from mcphub.mcp_servers.params import MCPServersParams, MCPServerConfig
from mcphub.mcp_servers.exceptions import ServerConfigNotFoundError, SetupError


class TestMCPServers:
    
    @mock.patch('subprocess.run')
    @mock.patch('pathlib.Path.exists')
    @mock.patch('pathlib.Path.chmod')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    def test_run_setup_script_success(self, mock_open, mock_chmod, mock_exists, mock_run, temp_config_file, mock_current_dir):
        """Test successful setup script execution."""
        # Mock Path.exists to return True for all paths
        mock_exists.return_value = True
        
        # Mock subprocess.run to simulate successful script execution
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # Create a valid JSON config for testing
        config_content = {
            "mcpServers": {
                "test-server": {
                    "package_name": "test-mcp-server",
                    "command": "python",
                    "args": ["-m", "test_server"],
                    "env": {"TEST_ENV": "test_value"}
                }
            }
        }
        
        # Create a temp directory path to use as script_path
        script_path = mock_current_dir / "temp_scripts"
        
        # Create a patched MCPServersParams class that doesn't attempt to read from disk
        with mock.patch('mcphub.mcp_servers.params.MCPServersParams._load_user_config', 
                        return_value=config_content.get('mcpServers', {})), \
             mock.patch('mcphub.mcp_servers.params.MCPServersParams._load_predefined_servers_params', 
                       return_value={}), \
             mock.patch('pathlib.Path.unlink'):  # Mock unlink to prevent file deletion errors
            
            params = MCPServersParams(str(temp_config_file))
            
            # Setup MCPServers with mocked _setup_all_servers
            with mock.patch.object(MCPServers, '_setup_all_servers'):
                servers = MCPServers(params)
                
                setup_script = "npm install"
                
                servers._run_setup_script(script_path, setup_script)
                
                # Check that the temporary script was created with correct content
                mock_open.assert_called_with(script_path / "setup_temp.sh", "w")
                mock_open().write.assert_any_call("#!/bin/bash\n")
                mock_open().write.assert_any_call(setup_script + "\n")
                
                # Check that chmod was called to make script executable
                mock_chmod.assert_called_once()
                
                # Check that the script was executed with correct parameters
                mock_run.assert_called_once()
                args, kwargs = mock_run.call_args
                assert str(script_path / "setup_temp.sh") in str(args[0])
                assert kwargs["cwd"] == script_path
    
    @mock.patch('subprocess.run')
    @mock.patch('pathlib.Path.exists')
    def test_run_setup_script_failure(self, mock_exists, mock_run, temp_config_file, mock_current_dir):
        """Test failed setup script execution."""
        mock_exists.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(1, "setup_script", stderr="Script failed")
        
        # Initialize MCPServersParams and MCPServers with mock _setup_all_servers
        params = MCPServersParams(str(temp_config_file))
        with mock.patch.object(MCPServers, '_setup_all_servers'):
            servers = MCPServers(params)
            
            with pytest.raises(SetupError):
                servers._run_setup_script(Path("/test/path"), "npm install")
    
    @mock.patch.object(MCPServers, '_clone_repository')
    @mock.patch.object(MCPServers, '_run_setup_script')
    @mock.patch.object(MCPServers, '_update_server_path')
    @mock.patch('pathlib.Path.exists')
    def test_setup_server(self, mock_exists, mock_update_path, mock_run_setup, mock_clone, temp_config_file, mock_current_dir):
        """Test setting up a server."""
        mock_exists.return_value = True
        mock_clone.return_value = Path("/test/repo")
        
        # Create a server config with repo_url and setup_script
        server_config = MCPServerConfig(
            package_name="test-mcp-server",
            command="python",
            args=["-m", "test_server"],
            env={"TEST_ENV": "test_value"},
            description="Test MCP Server",
            tags=["test", "demo"],
            repo_url="https://github.com/test/repo.git",
            setup_script="npm install"
        )
        
        # Mock the servers_params directly to avoid file access
        with mock.patch('mcphub.mcp_servers.params.MCPServersParams._load_user_config',
                       return_value={"test-server": {
                            "package_name": "test-mcp-server",
                            "command": "python",
                            "args": ["-m", "test_server"],
                            "env": {"TEST_ENV": "test_value"},
                            "repo_url": "https://github.com/test/repo.git",
                            "setup_script": "npm install"
                        }}), \
             mock.patch('mcphub.mcp_servers.params.MCPServersParams._load_predefined_servers_params',
                       return_value={}):
            
            params = MCPServersParams(str(temp_config_file))
            
            # Override the _servers_params attribute directly
            params._servers_params = {"test-mcp-server": server_config}
            
            # Mock the retrieve_server_params method to return our custom server_config
            params.retrieve_server_params = mock.MagicMock(return_value=server_config)
            
            with mock.patch.object(MCPServers, '_setup_all_servers'):
                servers = MCPServers(params)
                servers.setup_server(server_config)
                
                # Check that clone_repository and run_setup_script were called with correct args
                mock_clone.assert_called_once_with("https://github.com/test/repo.git", "test-mcp-server")
                mock_run_setup.assert_called_once_with(Path("/test/repo"), "npm install")
    
    @mock.patch('mcphub.mcp_servers.servers.MCPServerStdio')
    @mock.patch('mcphub.mcp_servers.servers.MCPServerStdioParams')  # Fix: Updated mock path to match import in servers.py
    @mock.patch('pathlib.Path.exists')
    def test_make_openai_mcp_server(self, mock_exists, mock_mcp_params, mock_mcp_server, temp_config_file, mock_current_dir):
        """Test creating an OpenAI MCP server."""
        mock_exists.return_value = True
        
        # Mock the return value for MCPServerStdioParams
        mock_params_instance = mock.MagicMock()
        mock_mcp_params.return_value = mock_params_instance
        
        # Initialize MCPServersParams and MCPServers with custom setup
        with mock.patch('mcphub.mcp_servers.params.MCPServersParams._load_user_config',
                       return_value={"test-server": {
                            "package_name": "test-mcp-server",
                            "command": "python",
                            "args": ["-m", "test_server"],
                            "env": {"TEST_ENV": "test_value"}
                        }}), \
             mock.patch('mcphub.mcp_servers.params.MCPServersParams._load_predefined_servers_params',
                       return_value={}):
             
            # Create MCPServersParams
            params = MCPServersParams(str(temp_config_file))
            
            # Create a server config and manually add it to _servers_params
            server_config = MCPServerConfig(
                package_name="test-mcp-server",
                command="python",
                args=["-m", "test_server"],
                env={"TEST_ENV": "test_value"},
                description="Test MCP Server",
                tags=["test", "demo"]
            )
            params._servers_params = {"test-server": server_config}
            
            # Mock the retrieve_server_params method
            params.retrieve_server_params = mock.MagicMock(
                side_effect=lambda name: server_config if name == "test-server" else None
            )
            
            with mock.patch.object(MCPServers, '_setup_all_servers'):
                servers = MCPServers(params)
                server = servers.make_openai_mcp_server("test-server")
                
                # Check that MCPServerStdioParams was called correctly
                mock_mcp_params.assert_called_once_with(
                    command="python",
                    args=["-m", "test_server"],
                    env={"TEST_ENV": "test_value"},
                    cwd=None
                )
                
                # Check that MCPServerStdio was created with correct params
                mock_mcp_server.assert_called_once_with(
                    params=mock_params_instance,
                    cache_tools_list=True
                )
                
                # Test with non-existent server
                with pytest.raises(ServerConfigNotFoundError):
                    servers.make_openai_mcp_server("non-existent")
    
    @mock.patch('mcphub.mcp_servers.servers.MCPServerStdio')
    @mock.patch('langchain_mcp_adapters.tools.load_mcp_tools')
    @mock.patch('pathlib.Path.exists')
    async def test_get_langchain_mcp_tools(self, mock_exists, mock_load_tools, mock_server, temp_config_file, mock_current_dir):
        """Test getting Langchain MCP tools."""
        mock_exists.return_value = True
        
        # Mock the context manager and async operations
        mock_server_instance = mock.AsyncMock()
        mock_server.return_value.__aenter__.return_value = mock_server_instance
        mock_load_tools.return_value = ["tool1", "tool2"]
        
        # Initialize MCPServersParams and MCPServers with mock _setup_all_servers
        params = MCPServersParams(str(temp_config_file))
        with mock.patch.object(MCPServers, '_setup_all_servers'):
            servers = MCPServers(params)
            tools = await servers.get_langchain_mcp_tools("test-server")
            
            assert tools == ["tool1", "tool2"]
            mock_load_tools.assert_called_once()
    
    @mock.patch('mcphub.mcp_servers.servers.MCPServerStdio')
    @mock.patch('autogen_ext.tools.mcp.StdioMcpToolAdapter.from_server_params')
    @mock.patch('pathlib.Path.exists')
    async def test_make_autogen_mcp_adapters(self, mock_exists, mock_adapter, mock_server, temp_config_file, mock_current_dir):
        """Test creating Autogen MCP adapters."""
        mock_exists.return_value = True
        
        # Mock the server instance and tool listing
        mock_server_instance = mock.AsyncMock()
        mock_server_instance.list_tools.return_value = [
            mock.MagicMock(name="tool1"),
            mock.MagicMock(name="tool2")
        ]
        mock_server.return_value.__aenter__.return_value = mock_server_instance
        
        # Mock the adapter creation
        mock_adapter.side_effect = ["adapter1", "adapter2"]
        
        # Initialize MCPServersParams and MCPServers with mock _setup_all_servers
        params = MCPServersParams(str(temp_config_file))
        with mock.patch.object(MCPServers, '_setup_all_servers'):
            servers = MCPServers(params)
            adapters = await servers.make_autogen_mcp_adapters("test-server")
            
            assert adapters == ["adapter1", "adapter2"]
            assert mock_adapter.call_count == 2
    
    @mock.patch('mcphub.mcp_servers.servers.MCPServerStdio')
    @mock.patch('pathlib.Path.exists')
    async def test_list_tools(self, mock_exists, mock_server, temp_config_file, mock_current_dir):
        """Test listing tools from an MCP server."""
        mock_exists.return_value = True
        
        # Mock the server instance
        mock_server_instance = mock.AsyncMock()
        mock_server_instance.list_tools.return_value = ["tool1", "tool2"]
        mock_server.return_value.__aenter__.return_value = mock_server_instance
        
        # Initialize MCPServersParams and MCPServers with mock _setup_all_servers
        params = MCPServersParams(str(temp_config_file))
        with mock.patch.object(MCPServers, '_setup_all_servers'):
            servers = MCPServers(params)
            tools = await servers.list_tools("test-server")
            
            assert tools == ["tool1", "tool2"]
            mock_server_instance.list_tools.assert_called_once()
    
    @mock.patch('subprocess.run')
    @mock.patch('pathlib.Path.exists')
    @mock.patch.object(MCPServers, '_get_cache_dir')
    def test_clone_repository_success(self, mock_get_cache_dir, mock_exists, mock_run, temp_config_file, mock_current_dir):
        """Test successful repository cloning."""
        # Mock the cache directory
        mock_cache_dir = mock_current_dir / ".mcphub_cache"
        mock_get_cache_dir.return_value = mock_cache_dir
        
        # Set up mocks for subprocess and exists
        mock_exists.return_value = False  # Repository doesn't exist yet
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # Initialize MCPServersParams and MCPServers with mock _setup_all_servers
        params = MCPServersParams(str(temp_config_file))
        with mock.patch.object(MCPServers, '_setup_all_servers'):
            servers = MCPServers(params)
            
            # Test cloning repository
            repo_url = "https://github.com/test/repo.git"
            repo_name = "test/repo"
            result = servers._clone_repository(repo_url, repo_name)
            
            # Expected result should be the cache_dir / repo
            expected_path = mock_cache_dir / "repo"
            assert result == expected_path
            
            # Check that git clone was called with correct parameters
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert args[0] == ["git", "clone", repo_url, str(expected_path)]
            assert kwargs["check"] == True
            assert kwargs["capture_output"] == True
            assert kwargs["text"] == True

    @mock.patch('subprocess.run')
    @mock.patch('pathlib.Path.exists')
    @mock.patch.object(MCPServers, '_get_cache_dir')
    def test_clone_repository_failure(self, mock_get_cache_dir, mock_exists, mock_run, temp_config_file, mock_current_dir):
        """Test failed repository cloning."""
        # Mock the cache directory
        mock_cache_dir = mock_current_dir / ".mcphub_cache"
        mock_get_cache_dir.return_value = mock_cache_dir
        
        # Set up mocks
        mock_exists.return_value = False  # Repository doesn't exist yet
        mock_run.side_effect = subprocess.CalledProcessError(
            128, "git clone", stderr="Error: Repository not found"
        )
        
        # Initialize MCPServersParams and MCPServers with mock _setup_all_servers
        params = MCPServersParams(str(temp_config_file))
        with mock.patch.object(MCPServers, '_setup_all_servers'):
            servers = MCPServers(params)
            
            # Test with invalid repo URL
            repo_url = "https://github.com/invalid/repo.git"
            repo_name = "invalid/repo"
            
            # Should raise SetupError
            with pytest.raises(SetupError) as exc_info:
                servers._clone_repository(repo_url, repo_name)
                
            # Check error message
            assert f"Failed to clone repository {repo_url}" in str(exc_info.value)
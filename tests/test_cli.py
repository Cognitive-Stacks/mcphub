"""Unit tests for mcphub CLI commands."""
import json
import os
import sys
from pathlib import Path
from unittest import mock
import pytest

from mcphub.cli import commands, utils


@pytest.fixture
def mock_cli_config_file(tmp_path):
    """Create a temporary .mcphub.json file for CLI testing."""
    config_content = {
        "mcpServers": {
            "test-server": {
                "package_name": "test-mcp-server",
                "command": "python",
                "args": ["-m", "test_server"],
                "env": {"TEST_ENV": "test_value"},
                "description": "Test MCP Server",
                "tags": ["test", "demo"]
            }
        }
    }
    
    config_file = tmp_path / ".mcphub.json"
    with open(config_file, "w") as f:
        json.dump(config_content, f)
    
    return config_file


@pytest.fixture
def mock_preconfigured_servers(tmp_path):
    """Create a mock preconfigured servers file for CLI testing."""
    content = {
        "mcpServers": {
            "test-server": {
                "package_name": "test-server",
                "command": "python",
                "args": ["-m", "test_server"],
                "env": {"TEST_ENV": "test_value"},
                "description": "Test MCP Server",
                "tags": ["test", "demo"]
            },
            "env-server": {
                "package_name": "env-server",
                "command": "python",
                "args": ["-m", "env_server"],
                "env": {"API_KEY": "${API_KEY}", "BASE_URL": "${BASE_URL}"},
                "description": "Server with Environment Variables",
                "tags": ["env", "test"]
            }
        }
    }
    
    file_path = tmp_path / "mcphub_preconfigured_servers.json"
    with open(file_path, "w") as f:
        json.dump(content, f)
    
    return file_path


@pytest.fixture
def cli_env(mock_cli_config_file, mock_preconfigured_servers, monkeypatch):
    """Set up the environment for CLI testing."""
    # Mock get_config_path to return our test config
    def mock_get_config_path():
        return mock_cli_config_file
    
    # Mock load_preconfigured_servers to use our test preconfigured servers
    def mock_load_preconfigured():
        with open(mock_preconfigured_servers, "r") as f:
            return json.load(f)
    
    # Apply patches
    monkeypatch.setattr(utils, "get_config_path", mock_get_config_path)
    monkeypatch.setattr(utils, "load_preconfigured_servers", mock_load_preconfigured)
    
    # Return paths for test verification
    return {
        "config_path": mock_cli_config_file,
        "preconfigured_path": mock_preconfigured_servers
    }


class TestCliInit:
    def test_init_creates_config_when_missing(self, cli_env, monkeypatch, tmp_path):
        """Test that 'init' command creates a new config file when it doesn't exist."""
        # Set up a different config path that doesn't exist yet
        new_config_path = tmp_path / "new_config_dir" / ".mcphub.json"
        new_config_path.parent.mkdir(exist_ok=True)
        
        def mock_get_config_path():
            return new_config_path
        
        monkeypatch.setattr(utils, "get_config_path", mock_get_config_path)
        
        # Execute init command
        args = mock.Mock()
        commands.init_command(args)
        
        # Verify config was created
        assert new_config_path.exists()
        with open(new_config_path, "r") as f:
            config = json.load(f)
            assert config == utils.DEFAULT_CONFIG

    def test_init_skips_when_config_exists(self, cli_env, capfd):
        """Test that 'init' command skips creation when config already exists."""
        # Execute init command
        args = mock.Mock()
        commands.init_command(args)
        
        # Verify output indicates config already exists
        out, _ = capfd.readouterr()
        assert "already exists" in out


class TestCliAdd:
    def test_add_server_success(self, cli_env):
        """Test adding a server from preconfigured servers."""
        # Set up command arguments
        args = mock.Mock()
        args.mcp_name = "test-server"
        args.non_interactive = True
        
        # Execute add command
        commands.add_command(args)
        
        # Verify server was added to config
        with open(cli_env["config_path"], "r") as f:
            config = json.load(f)
        
        assert "test-server" in config["mcpServers"]
        assert config["mcpServers"]["test-server"]["command"] == "python"

    def test_add_nonexistent_server(self, cli_env, capfd, monkeypatch):
        """Test adding a server that doesn't exist in preconfigured servers."""
        # Set up command arguments
        args = mock.Mock()
        args.mcp_name = "nonexistent-server"
        args.non_interactive = True
        
        # Mock sys.exit to avoid test termination
        monkeypatch.setattr(sys, "exit", lambda x: None)
        
        # Execute add command
        commands.add_command(args)
        
        # Verify error message
        out, _ = capfd.readouterr()
        assert "Error: MCP server 'nonexistent-server' not found" in out
        assert "Available preconfigured servers" in out

    @mock.patch("builtins.input", side_effect=["test_api_key", "https://test.com"])
    def test_add_server_with_env_vars(self, mock_input, cli_env, monkeypatch):
        """Test adding a server that requires environment variables."""
        # Set up command arguments
        args = mock.Mock()
        args.mcp_name = "env-server"
        args.non_interactive = False
        
        # Execute add command
        commands.add_command(args)
        
        # Verify server was added with environment variables
        with open(cli_env["config_path"], "r") as f:
            config = json.load(f)
        
        assert "env-server" in config["mcpServers"]
        assert config["mcpServers"]["env-server"]["env"]["API_KEY"] == "test_api_key"
        assert config["mcpServers"]["env-server"]["env"]["BASE_URL"] == "https://test.com"

    @mock.patch("builtins.input", side_effect=["", ""])
    def test_add_server_missing_env_vars(self, mock_input, cli_env, capfd):
        """Test adding a server with missing environment variables."""
        # Set up command arguments
        args = mock.Mock()
        args.mcp_name = "env-server"
        args.non_interactive = False
        
        # Execute add command
        commands.add_command(args)
        
        # Verify warning about missing environment variables
        out, _ = capfd.readouterr()
        assert "Warning: The following environment variables are required but not set" in out
        assert "API_KEY" in out
        assert "BASE_URL" in out


class TestCliRemove:
    def test_remove_existing_server(self, cli_env, capfd):
        """Test removing a server that exists in the config."""
        # First ensure the server exists in config
        with open(cli_env["config_path"], "r") as f:
            config = json.load(f)
            config["mcpServers"]["server-to-remove"] = {"command": "test"}
        
        with open(cli_env["config_path"], "w") as f:
            json.dump(config, f)
        
        # Set up command arguments
        args = mock.Mock()
        args.mcp_name = "server-to-remove"
        
        # Execute remove command
        commands.remove_command(args)
        
        # Verify server was removed
        with open(cli_env["config_path"], "r") as f:
            config = json.load(f)
        
        assert "server-to-remove" not in config["mcpServers"]
        
        # Check output
        out, _ = capfd.readouterr()
        assert "Removed configuration for 'server-to-remove'" in out

    def test_remove_nonexistent_server(self, cli_env, capfd, monkeypatch):
        """Test removing a server that doesn't exist in the config."""
        # Set up command arguments
        args = mock.Mock()
        args.mcp_name = "nonexistent-server"
        
        # Mock sys.exit to avoid test termination
        monkeypatch.setattr(sys, "exit", lambda x: None)
        
        # Execute remove command
        commands.remove_command(args)
        
        # Verify error message
        out, _ = capfd.readouterr()
        assert "Error: MCP server 'nonexistent-server' not found" in out


class TestCliList:
    def test_list_configured_servers(self, cli_env, capfd):
        """Test listing configured servers."""
        # Prepare config with multiple servers
        with open(cli_env["config_path"], "r") as f:
            config = json.load(f)
            
        config["mcpServers"] = {
            "server1": {"command": "test1"},
            "server2": {"command": "test2"}
        }
        
        with open(cli_env["config_path"], "w") as f:
            json.dump(config, f)
        
        # Set up command arguments
        args = mock.Mock()
        args.all = False
        
        # Execute list command
        commands.list_command(args)
        
        # Verify output
        out, _ = capfd.readouterr()
        assert "Configured MCP servers:" in out
        assert "- server1" in out
        assert "- server2" in out
        assert "Available preconfigured MCP servers:" not in out

    def test_list_all_servers(self, cli_env, capfd):
        """Test listing all servers including preconfigured ones."""
        # Set up command arguments
        args = mock.Mock()
        args.all = True
        
        # Execute list command
        commands.list_command(args)
        
        # Verify output
        out, _ = capfd.readouterr()
        assert "Configured MCP servers:" in out
        assert "Available preconfigured MCP servers:" in out
        assert "- test-server" in out
        assert "- env-server" in out


class TestCliUtils:
    def test_detect_env_vars(self):
        """Test detecting environment variables in a server config."""
        server_config = {
            "command": "test",
            "env": {
                "API_KEY": "${API_KEY}",
                "DEBUG": "true",
                "URL": "${BASE_URL}"
            }
        }
        
        env_vars = utils.detect_env_vars(server_config)
        
        assert sorted(env_vars) == sorted(["API_KEY", "BASE_URL"])
        assert "DEBUG" not in env_vars

    def test_process_env_vars(self):
        """Test processing environment variables in a server config."""
        server_config = {
            "command": "test",
            "env": {
                "API_KEY": "${API_KEY}",
                "DEBUG": "true",
                "URL": "${BASE_URL}"
            }
        }
        
        env_values = {
            "API_KEY": "test_key",
            # BASE_URL intentionally missing
        }
        
        processed = utils.process_env_vars(server_config, env_values)
        
        assert processed["env"]["API_KEY"] == "test_key"
        assert processed["env"]["DEBUG"] == "true"
        assert processed["env"]["URL"] == "${BASE_URL}"  # unchanged

    @mock.patch.dict(os.environ, {"ENV_VAR": "env_value"})
    def test_add_server_with_env_var_from_environment(self, cli_env, monkeypatch):
        """Test adding a server using environment variables from system environment."""
        # Modify preconfigured servers to include our test env var
        with open(cli_env["preconfigured_path"], "r") as f:
            preconfig = json.load(f)
        
        preconfig["mcpServers"]["env-test"] = {
            "command": "test",
            "env": {"TEST_VAR": "${ENV_VAR}"}
        }
        
        with open(cli_env["preconfigured_path"], "w") as f:
            json.dump(preconfig, f)
        
        # Mock user input to skip (use env var from environment)
        monkeypatch.setattr("builtins.input", lambda _: "")
        
        # Add server
        success, missing = utils.add_server_config("env-test", interactive=True)
        
        # Verify
        assert success is True
        assert missing is None
        
        # Check config
        with open(cli_env["config_path"], "r") as f:
            config = json.load(f)
        
        assert "env-test" in config["mcpServers"]
        # The env var template should be preserved (it will be resolved at runtime)
        assert config["mcpServers"]["env-test"]["env"]["TEST_VAR"] == "${ENV_VAR}"


class TestCliParsing:
    @mock.patch("mcphub.cli.commands.init_command")
    def test_parse_init_command(self, mock_init, monkeypatch):
        """Test that 'init' command is properly parsed and dispatched."""
        # Mock sys.argv
        monkeypatch.setattr(sys, "argv", ["mcphub", "init"])
        
        # Call main() which should parse arguments and dispatch
        commands.main()
        
        # Verify init_command was called
        mock_init.assert_called_once()

    @mock.patch("mcphub.cli.commands.add_command")
    def test_parse_add_command(self, mock_add, monkeypatch):
        """Test that 'add' command is properly parsed and dispatched."""
        # Mock sys.argv
        monkeypatch.setattr(sys, "argv", ["mcphub", "add", "test-server"])
        
        # Call main() which should parse arguments and dispatch
        commands.main()
        
        # Verify add_command was called
        mock_add.assert_called_once()
        # Verify the arguments
        args = mock_add.call_args[0][0]
        assert args.mcp_name == "test-server"
        assert args.non_interactive is False

    @mock.patch("mcphub.cli.commands.add_command")
    def test_parse_add_command_noninteractive(self, mock_add, monkeypatch):
        """Test that 'add' command with --non-interactive flag is properly parsed."""
        # Mock sys.argv
        monkeypatch.setattr(sys, "argv", ["mcphub", "add", "--non-interactive", "test-server"])
        
        # Call main() which should parse arguments and dispatch
        commands.main()
        
        # Verify add_command was called
        mock_add.assert_called_once()
        # Verify the arguments
        args = mock_add.call_args[0][0]
        assert args.mcp_name == "test-server"
        assert args.non_interactive is True

    @mock.patch("mcphub.cli.commands.remove_command")
    def test_parse_remove_command(self, mock_remove, monkeypatch):
        """Test that 'remove' command is properly parsed and dispatched."""
        # Mock sys.argv
        monkeypatch.setattr(sys, "argv", ["mcphub", "remove", "test-server"])
        
        # Call main() which should parse arguments and dispatch
        commands.main()
        
        # Verify remove_command was called
        mock_remove.assert_called_once()
        # Verify the arguments
        args = mock_remove.call_args[0][0]
        assert args.mcp_name == "test-server"

    @mock.patch("mcphub.cli.commands.list_command")
    def test_parse_list_command(self, mock_list, monkeypatch):
        """Test that 'list' command is properly parsed and dispatched."""
        # Mock sys.argv
        monkeypatch.setattr(sys, "argv", ["mcphub", "list"])
        
        # Call main() which should parse arguments and dispatch
        commands.main()
        
        # Verify list_command was called
        mock_list.assert_called_once()
        # Verify the arguments
        args = mock_list.call_args[0][0]
        assert args.all is False

    @mock.patch("mcphub.cli.commands.list_command")
    def test_parse_list_command_all(self, mock_list, monkeypatch):
        """Test that 'list' command with --all flag is properly parsed."""
        # Mock sys.argv
        monkeypatch.setattr(sys, "argv", ["mcphub", "list", "--all"])
        
        # Call main() which should parse arguments and dispatch
        commands.main()
        
        # Verify list_command was called
        mock_list.assert_called_once()
        # Verify the arguments
        args = mock_list.call_args[0][0]
        assert args.all is True
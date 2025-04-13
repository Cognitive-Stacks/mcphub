import subprocess
from pathlib import Path
from typing import List

from agents.mcp import MCPServerStdio, MCPServerStdioParams
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools
from autogen_ext.tools.mcp import StdioMcpToolAdapter, StdioServerParams

from .exceptions import ServerConfigNotFoundError, SetupError
from .params import MCPServerConfig, MCPServersParams


class MCPServers:
    def __init__(self, servers_params: MCPServersParams):
        self.servers_params = servers_params
        self.cache_dir = self._get_cache_dir()
        # Run setup for all servers during initialization
        self._setup_all_servers()

    def _get_cache_dir(self) -> Path:
        """Get the cache directory path, creating it if it doesn't exist."""
        current_dir = Path.cwd()
        # First try to find a project root with .mcphub.json
        for parent in [current_dir] + list(current_dir.parents):
            if (parent / ".mcphub.json").exists():
                cache_dir = parent / ".mcphub_cache"
                cache_dir.mkdir(exist_ok=True)
                return cache_dir
        
        # If no .mcphub.json was found, create cache in the current working directory
        cache_dir = current_dir / ".mcphub_cache"
        cache_dir.mkdir(exist_ok=True)
        return cache_dir

    def _clone_repository(self, repo_url: str, repo_name: str) -> Path:
        """Clone a repository into the cache directory."""
        if not repo_url:
            raise SetupError(
                "Repository URL is required but was not provided. "
                "Please configure the repo_url field in .mcphub.json for this server."
            )
            
        repo_dir = self.cache_dir / repo_name.split('/')[-1]
        
        if repo_dir.exists():
            print(f"Repository already exists at {repo_dir}")
            return repo_dir

        try:
            subprocess.run(
                ["git", "clone", repo_url, str(repo_dir)],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"Successfully cloned repository to {repo_dir}")
            return repo_dir
        except subprocess.CalledProcessError as e:
            raise SetupError(f"Failed to clone repository {repo_url}: {e.stderr}")

    def _run_setup_script(self, script_path: Path, setup_script: str) -> None:
        """Run the setup script in the repository directory."""
        try:
            # Create a temporary shell script
            script_file = script_path / "setup_temp.sh"
            with open(script_file, "w") as f:
                f.write("#!/bin/bash\n")
                f.write(setup_script + "\n")
            
            # Make the script executable
            script_file.chmod(0o755)
            
            # Run the script
            subprocess.run(
                [str(script_file)],
                check=True,
                capture_output=True,
                text=True,
                cwd=script_path
            )
            
            # Clean up
            script_file.unlink()
            
            print(f"Successfully executed setup script: {setup_script} in {script_path}")
        except subprocess.CalledProcessError as e:
            raise SetupError(f"Failed to run setup script '{setup_script}' in {script_path}: {e.stderr}")
        except Exception as e:
            raise SetupError(f"Error during setup script execution: {str(e)}")

    def _update_server_path(self, server_config: MCPServerConfig, repo_dir: Path) -> None:
        """Update the server_path in the server configuration."""
        self.servers_params.update_server_path(server_config.package_name, str(repo_dir))
        print(f"Updated server path for {server_config.package_name}: {repo_dir}")

    def setup_server(self, server_config: MCPServerConfig) -> None:
        """Set up a single server if it has repo_url and setup_script."""
        if not (server_config.repo_url and server_config.setup_script):
            print(f"Skipping setup for {server_config.package_name}: No repo_url or setup_script specified")
            return

        try:
            # Clone the repository
            repo_dir = self._clone_repository(server_config.repo_url, server_config.package_name)
            
            # Run setup script
            if repo_dir.exists():
                self._run_setup_script(repo_dir, server_config.setup_script)
                # Update server_path after successful setup
                self._update_server_path(server_config, repo_dir)
            else:
                raise SetupError(f"Setup script not found: {repo_dir}")

        except (SetupError, FileNotFoundError) as e:
            print(f"Error setting up server {server_config.package_name}: {str(e)}")
            raise

    def _setup_all_servers(self) -> None:
        """Set up all servers that have repo_url and setup_script configured."""
        print("Starting setup of all MCP servers...")
        
        for server_config in self.servers_params.servers_params:
            try:
                self.setup_server(server_config)
            except Exception as e:
                print(f"Failed to set up server {server_config.package_name}: {str(e)}")
                # Continue with other servers even if one fails
                continue

        print("Completed server setup process")

    def make_openai_mcp_server(self, mcp_name: str, cache_tools_list: bool = True) -> MCPServerStdio:
        """
        Create and return an OpenAI MCP server for the given MCP name.
        
        Args:
            mcp_name: The name of the MCP server configuration to use
            cache_tools_list: Whether to cache the tools list (default: True)
            
        Returns:
            MCPServerStdio: The configured MCP server
            
        Raises:
            ServerConfigNotFoundError: If the server configuration is not found
        """
        server_config = self.servers_params.retrieve_server_params(mcp_name)
        if not server_config:
            raise ServerConfigNotFoundError(f"Server configuration not found for '{mcp_name}'")

        # Convert server config to StdioServerParameters
        server_params = MCPServerStdioParams(
            command=server_config.command,
            args=server_config.args,
            env=server_config.env,
            cwd=server_config.cwd
        )

        return MCPServerStdio(
            params=server_params,
            cache_tools_list=cache_tools_list
        )

    async def get_langchain_mcp_tools(self, mcp_name: str, cache_tools_list: bool = True) -> List[BaseTool]:
        """
        Get a list of Langchain tools from an MCP server.
        
        Args:
            mcp_name: The name of the MCP server configuration to use
            cache_tools_list: Whether to cache the tools list (default: True)
            
        Returns:
            List[Tool]: List of Langchain tools provided by the MCP server
            
        Raises:
            ServerConfigNotFoundError: If the server configuration is not found
        """
        async with self.make_openai_mcp_server(mcp_name, cache_tools_list) as server:
            tools = await load_mcp_tools(server.session)
            return tools
        
    async def make_autogen_mcp_adapters(self, mcp_name: str) -> List[StdioMcpToolAdapter]:
        server_config = self.servers_params.retrieve_server_params(mcp_name)
        if not server_config:
            raise ServerConfigNotFoundError(f"Server configuration not found for '{mcp_name}'")
        
        server_params = StdioServerParams(
            command=server_config.command,
            args=server_config.args,
            env=server_config.env,
            cwd=server_config.cwd
        )

        adapters = []
        async with self.make_openai_mcp_server(mcp_name, cache_tools_list=True) as server:
            for tool in await server.list_tools():
                adapter = await StdioMcpToolAdapter.from_server_params(server_params, tool.name)
                adapters.append(adapter)
        return adapters
    
    async def list_tools(self, mcp_name: str) -> List[BaseTool]:
        """
        List all tools from an MCP server.
        
        Args:
            mcp_name: The name of the MCP server configuration to use

        Returns:
            List[BaseTool]: List of tools provided by the MCP server
        """
        async with self.make_openai_mcp_server(mcp_name, cache_tools_list=True) as server:
            return await server.list_tools()

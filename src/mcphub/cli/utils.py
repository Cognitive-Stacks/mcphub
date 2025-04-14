"""Utility functions for the mcphub CLI."""
import json
import os
import re
import platform
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

DEFAULT_CONFIG = {
    "mcpServers": {}
}

def get_config_path() -> Path:
    """Get the path to the .mcphub.json config file."""
    return Path.cwd() / ".mcphub.json"

def load_config() -> Dict[str, Any]:
    """Load the config file if it exists, otherwise return an empty config dict."""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG

def save_config(config: Dict[str, Any]) -> None:
    """Save the config to the .mcphub.json file."""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

def load_preconfigured_servers() -> Dict[str, Any]:
    """Load the preconfigured servers from mcphub_preconfigured_servers.json."""
    preconfigured_path = Path(__file__).parent.parent / "mcphub_preconfigured_servers.json"
    if preconfigured_path.exists():
        with open(preconfigured_path, "r") as f:
            return json.load(f)
    return {"mcpServers": {}}

def detect_env_vars(server_config: Dict[str, Any]) -> List[str]:
    """Detect environment variables in a server configuration.
    
    Args:
        server_config: Server configuration dict
        
    Returns:
        List of environment variable names found in the configuration
    """
    env_vars = []
    
    # Check if the server has env section
    if "env" in server_config and isinstance(server_config["env"], dict):
        for key, value in server_config["env"].items():
            # Check if value is a template like ${ENV_VAR}
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]  # Extract ENV_VAR from ${ENV_VAR}
                env_vars.append(env_var)
    
    return env_vars

def prompt_env_vars(env_vars: List[str]) -> Dict[str, str]:
    """Prompt the user for environment variable values.
    
    Args:
        env_vars: List of environment variable names to prompt for
        
    Returns:
        Dictionary mapping environment variable names to values
    """
    values = {}
    
    print("\nThis MCP server requires environment variables to be set.")
    print("You can either:")
    print("1. Enter values now (they will be saved in your .mcphub.json)")
    print("2. Set them in your environment and press Enter to skip")
    
    for var in env_vars:
        # Check if the environment variable is already set
        existing_value = os.environ.get(var)
        if existing_value:
            prompt = f"Environment variable {var} found in environment. Press Enter to use it or provide a new value: "
        else:
            prompt = f"Enter value for {var} (or press Enter to skip): "
        
        value = input(prompt)
        
        # If user entered a value, save it
        if value:
            values[var] = value
    
    return values

def process_env_vars(server_config: Dict[str, Any], env_values: Dict[str, str]) -> Dict[str, Any]:
    """Process environment variables in a server configuration.
    
    Args:
        server_config: Server configuration dict
        env_values: Dictionary of environment variable values
        
    Returns:
        Updated server configuration with processed environment variables
    """
    # Create a copy of the config to avoid modifying the original
    config = server_config.copy()
    
    # If there's no env section, nothing to do
    if "env" not in config or not isinstance(config["env"], dict):
        return config
    
    # New env dict to store processed values
    new_env = {}
    
    for key, value in config["env"].items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]  # Extract ENV_VAR from ${ENV_VAR}
            
            # Use provided value or environment variable
            if env_var in env_values:
                new_env[key] = env_values[env_var]
            else:
                # Keep the template if not provided
                new_env[key] = value
        else:
            # Keep non-template values as is
            new_env[key] = value
    
    # Update the env section
    config["env"] = new_env
    return config

def add_server_config(name: str, interactive: bool = True, save_to_config: bool = True) -> Tuple[bool, Optional[List[str]]]:
    """Add a preconfigured server to the local config.
    
    Args:
        name: Name of the preconfigured server to add
        interactive: Whether to prompt for environment variables
        save_to_config: Whether to save the server to the local .mcphub.json file
        
    Returns:
        Tuple of (success, missing_env_vars):
          - success: True if the server was added, False if it wasn't found
          - missing_env_vars: List of environment variables that weren't set (None if no env vars needed)
    """
    preconfigured = load_preconfigured_servers()
    if name not in preconfigured.get("mcpServers", {}):
        return False, None
    
    # Get the server config
    server_config = preconfigured["mcpServers"][name]
    
    # Detect environment variables
    env_vars = detect_env_vars(server_config)
    missing_env_vars = []
    
    # Process environment variables if needed
    if env_vars and interactive:
        env_values = prompt_env_vars(env_vars)
        server_config = process_env_vars(server_config, env_values)
        
        # Check for missing environment variables
        for var in env_vars:
            if var not in env_values and var not in os.environ:
                missing_env_vars.append(var)
    
    # Save to config if requested
    if save_to_config:
        config = load_config()
        if "mcpServers" not in config:
            config["mcpServers"] = {}
        
        config["mcpServers"][name] = server_config
        save_config(config)
    
    return True, missing_env_vars if missing_env_vars else None

def remove_server_config(name: str) -> bool:
    """Remove a server config from the local .mcphub.json file.
    
    Args:
        name: Name of the server to remove
        
    Returns:
        bool: True if the server was removed, False if it wasn't in the config
    """
    config = load_config()
    if name in config.get("mcpServers", {}):
        del config["mcpServers"][name]
        save_config(config)
        return True
    return False

def list_available_servers() -> Dict[str, Any]:
    """List all available preconfigured servers."""
    preconfigured = load_preconfigured_servers()
    return preconfigured.get("mcpServers", {})

def list_configured_servers() -> Dict[str, Any]:
    """List all servers in the local config."""
    config = load_config()
    return config.get("mcpServers", {})

def get_claude_desktop_config_path() -> Optional[Path]:
    """Get the path to Claude desktop configuration file based on the operating system.
    
    Returns:
        Path object to the configuration file or None if the OS is not supported
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        print(f"Detected Windows OS: {system}")
        appdata = os.environ.get("AppData")
        if not appdata:
            return None
        print(Path(appdata) / "Claude" / "claude_desktop_config.json")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    
    raise NotImplementedError(f"Unsupported operating system: {system}")

def update_claude_desktop_config(mcp_server_name: str) -> Tuple[bool, Optional[str]]:
    """Update Claude desktop configuration file to use the specified MCP server.
    
    Args:
        mcp_server_name: Name of the MCP server to configure in Claude
        
    Returns:
        Tuple of (success, config_path):
          - success: True if the configuration was updated, False otherwise
          - config_path: Path to the configuration file or None if failed
    """
    # Get the path to Claude's configuration file
    config_path = get_claude_desktop_config_path()
    print(f"Claude config path: {config_path}")
    if not config_path:
        return False, None
    
    # Ensure the directory exists
    config_dir = config_path.parent
    if not config_dir.exists():
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            return False, None
    
    # Load the existing configuration if it exists
    claude_config = {}
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                claude_config = json.load(f)
        except Exception:
            # If the file exists but can't be parsed, start with an empty config
            claude_config = {}
    
    # Load the MCPHub configuration to get the server details
    mcphub_config = load_config()
    server_config = mcphub_config.get("mcpServers", {}).get(mcp_server_name)    
    # Ensure the mcpServers key exists in claude_config
    if "mcpServers" not in claude_config:
        claude_config["mcpServers"] = {}
    
    # Update Claude's configuration with MCP settings
    claude_config["mcpServers"][mcp_server_name] = server_config

    print(claude_config)
    
    # Add any additional settings needed for Claude's MCP integration
    # This can be expanded as needed for future Claude desktop app versions
    
    # Save the configuration file
    try:
        with open(config_path, "w") as f:
            json.dump(claude_config, f, indent=2)
        return True, str(config_path)
    except Exception:
        return False, None
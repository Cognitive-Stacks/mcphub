try:
    from agents.mcp import MCPServerStdio, MCPServerStdioParams
    from .base import MCPBaseAdapter

    class MCPOpenAIAgentsAdapter(MCPBaseAdapter):
        def create_server(self, mcp_name: str, cache_tools_list: bool = True) -> MCPServerStdio:
            server_config = self.get_server_config(mcp_name)
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
except ImportError:
    class MCPOpenAIAgentsAdapter:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError("OpenAI Agents dependencies not found. Install with: pip install mcphub[openai]") 
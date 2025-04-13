

try:
    from typing import List

    from langchain_core.tools import BaseTool
    from langchain_mcp_adapters.tools import load_mcp_tools

    from .base import MCPBaseAdapter

    class MCPLangChainAdapter(MCPBaseAdapter):
        async def create_tools(self, mcp_name: str) -> List[BaseTool]:
            async with self.create_session(mcp_name) as session:
                return await load_mcp_tools(session)

except ImportError:
    class MCPLangChainAdapter:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError("LangChain dependencies not found. Install with: pip install mcphub[langchain]") 
"""SAGE MCP Server - Model Context Protocol integration.

Exposes SAGE functionality as MCP tools for ChatGPT Apps
and Claude Desktop integration.
"""

from .server import create_mcp_server, mcp

__all__ = ["create_mcp_server", "mcp"]

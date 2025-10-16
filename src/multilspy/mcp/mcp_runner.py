"""
MCP (Model Context Protocol) runner for multilspy language servers.

This module provides MCP tool definitions that expose multilspy language server
functionality through the Model Context Protocol using the fastmcp framework.
It uses an `lsp.toml` configuration file to determine which language servers to start
and how to configure them.

Key improvements:
1. Uses fastmcp framework for standardized MCP tool management
2. Derives schemas from LSP protocol types rather than manually creating them
3. Initializes language servers at startup once, keeps them running
4. Intercepts and validates lsp.toml configuration at initialization
5. Each tool checks for configuration at call time as fallback
"""

import asyncio
import json
import logging
import os
import pathlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from multilspy.lsp_protocol_handler import lsp_types
from multilspy.lsp_protocol_handler.lsp_types import TextDocumentIdentifier

try:
    import tomllib
except ModuleNotFoundError:
    # Python < 3.11
    import tomli as tomllib

from fastmcp import Server

from multilspy.language_server import SyncLanguageServer
from multilspy.multilspy_config import MultilspyConfig, Language
from multilspy.multilspy_logger import MultilspyLogger
from multilspy.multilspy_exceptions import MultilspyException


LSP_TOML_SCHEMA = """
# LSP Configuration for multilspy MCP

# Main LSP configuration section
[lsp]
# List of language servers to start (e.g., ["java", "python", "rust"])
language_servers = ["java"]

# Java language server configuration (optional)
[lsp.java]
# List of Java project roots (workspace directories)
roots = ["/path/to/java/project"]

# Java version (optional, defaults to system default)
# java_version = "17"

# Gradle version (optional, defaults to 7.3.3)
# gradle_version = "7.3.3"

# Python language server configuration (optional)
[lsp.python]
roots = ["/path/to/python/project"]

# Rust language server configuration (optional)
[lsp.rust]
roots = ["/path/to/rust/project"]

# TypeScript/JavaScript configuration (optional)
[lsp.typescript]
roots = ["/path/to/ts/project"]

# Go configuration (optional)
[lsp.go]
roots = ["/path/to/go/project"]

# C# configuration (optional)
[lsp.csharp]
roots = ["/path/to/csharp/project"]

# Other supported languages: kotlin, ruby, dart, cpp
# [lsp.kotlin]
# roots = ["/path/to/kotlin/project"]
"""


@dataclass
class LanguageServerConfig:
    """Configuration for a single language server instance."""

    language: Language
    roots: List[str] = field(default_factory=list)
    java_version: Optional[str] = None
    gradle_version: Optional[str] = None

    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate the language server configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.roots:
            return False, f"No roots specified for language server {self.language}"

        for root in self.roots:
            if not os.path.isdir(root):
                return False, f"Root path does not exist: {root}"

        return True, None


@dataclass
class LSPConfig:
    """Main LSP configuration loaded from lsp.toml."""

    language_servers: List[Language] = field(default_factory=list)
    servers: Dict[Language, LanguageServerConfig] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "LSPConfig":
        """
        Create an LSPConfig from a dictionary (loaded from TOML).

        Args:
            config_dict: Dictionary loaded from lsp.toml

        Returns:
            LSPConfig instance

        Raises:
            MultilspyException: If configuration is invalid
        """
        lsp_section = config_dict.get("lsp", {})
        language_servers_str = lsp_section.get("language_servers", [])

        # Convert string language names to Language enum
        language_servers = []
        for lang_str in language_servers_str:
            try:
                lang = Language(lang_str.lower())
                language_servers.append(lang)
            except ValueError:
                raise MultilspyException(f"Unsupported language: {lang_str}")

        # Load configuration for each language server
        servers = {}
        for lang in language_servers:
            lang_config_dict = lsp_section.get(lang.value, {})
            roots = lang_config_dict.get("roots", [])

            if not isinstance(roots, list):
                raise MultilspyException(f"'roots' for {lang.value} must be a list")

            server_config = LanguageServerConfig(
                language=lang,
                roots=roots,
                java_version=lang_config_dict.get("java_version"),
                gradle_version=lang_config_dict.get("gradle_version"),
            )

            # Validate
            is_valid, error_msg = server_config.validate()
            if not is_valid:
                raise MultilspyException(error_msg)

            servers[lang] = server_config

        return cls(language_servers=language_servers, servers=servers)

    def to_dict(self) -> Dict[str, Any]:
        """Convert LSPConfig to dictionary representation."""
        return {
            "language_servers": [lang.value for lang in self.language_servers],
            "servers": {
                lang.value: asdict(config) for lang, config in self.servers.items()
            },
        }


class MCPToolError(Exception):
    """Base exception for MCP tool errors."""

    pass


class LSPNotConfiguredException(MCPToolError):
    """Exception raised when lsp.toml is not found or not configured."""

    pass


class MCPRunner:
    """
    MCP runner that manages language servers and exposes them as MCP tools using fastmcp.

    This class handles:
    - Loading and validating lsp.toml configuration at initialization
    - Initializing language servers at startup (once, not per-request)
    - Managing language server lifecycle
    - Per-tool fallback configuration checking

    Key design improvements:
    1. Uses fastmcp Server for standardized MCP tool management
    2. Starts language servers once during __init__ and keeps them running
    3. Derives tool schemas from LSP protocol types
    4. Validates configuration at startup
    5. Each tool checks for configuration at call time and loads if available

    Workflow:
    - If lsp.toml exists at startup: config is loaded, servers start immediately
    - If lsp.toml missing at startup: servers stay null, all tools check for config at call time
    - If user creates lsp.toml and calls tool: tool detects config, loads it, starts servers, executes

    Example usage:
    ```python
    # Case 1: With existing lsp.toml
    runner = MCPRunner("/path/to/workspace")
    server = runner.create_mcp_server()
    # All tools work immediately

    # Case 2: Without lsp.toml (workflow with user)
    runner = MCPRunner("/path/to/workspace")
    server = runner.create_mcp_server()
    # User creates lsp.toml
    # User calls tool -> tool checks, loads config, starts servers, executes
    ```
    """

    def __init__(self, workspace_root: Optional[str] = None):
        """
        Initialize the MCP runner.

        If lsp.toml exists, loads it and starts language servers.
        If lsp.toml doesn't exist, defers loading until tool is called.

        Args:
            workspace_root: Root directory of the workspace. If None, uses current directory.
        """
        self.workspace_root = workspace_root or os.getcwd()
        self.logger = MultilspyLogger()
        self.config: Optional[LSPConfig] = None
        self.language_servers: Dict[Language, SyncLanguageServer] = {}
        self._server_contexts: Dict[Language, Any] = {}

        # Try to load configuration at initialization if it exists
        self._try_load_config()

        # Start language servers if config is available
        if self.config is not None:
            self._start_language_servers_internal()

    def _try_load_config(self) -> None:
        """
        Attempt to load lsp.toml configuration, but don't fail if missing.

        This allows the runner to work even without configuration, deferring
        the error until a tool is called.
        """
        lsp_toml_path = os.path.join(self.workspace_root, "lsp.toml")

        if not os.path.exists(lsp_toml_path):
            return

        try:
            with open(lsp_toml_path, "rb") as f:
                toml_dict = tomllib.load(f)
            self.config = LSPConfig.from_dict(toml_dict)
            self.logger.log(
                f"Loaded LSP configuration with servers: {[s.value for s in self.config.language_servers]}",
                logging.INFO,
            )
        except Exception as e:
            self.logger.log(
                f"Failed to load lsp.toml from {lsp_toml_path}: {str(e)}", logging.ERROR
            )
            # Don't raise - let tools check at call time

    def _ensure_configured(self) -> bool:
        """
        Check if configuration needs to be loaded at tool call time.

        If config is already loaded, returns True.
        If config wasn't loaded but file now exists, loads it and starts servers.
        If config still doesn't exist, returns False.

        Returns:
            True if configured (either already or just loaded), False if still not configured
        """
        if self.config is not None:
            # Already configured
            return True

        lsp_toml_path = os.path.join(self.workspace_root, "lsp.toml")

        if not os.path.exists(lsp_toml_path):
            # Still no config file
            return False

        # File exists now, try to load it
        try:
            with open(lsp_toml_path, "rb") as f:
                toml_dict = tomllib.load(f)
            self.config = LSPConfig.from_dict(toml_dict)
            self.logger.log(
                f"Loaded LSP configuration with servers: {[s.value for s in self.config.language_servers]}",
                logging.INFO,
            )

            # Start language servers now that config is loaded
            self._start_language_servers_internal()
            return True
        except Exception as e:
            self.logger.log(
                f"Failed to load lsp.toml from {lsp_toml_path}: {str(e)}", logging.ERROR
            )
            return False

    def _start_language_servers_internal(self) -> None:
        """
        Start all configured language servers at initialization (once).

        This is called once during __init__, not per-request. Servers are kept
        running and reused for all subsequent tool calls.

        Raises:
            MultilspyException: If language server initialization fails
        """
        if self.config is None:
            return

        for language, server_config in self.config.servers.items():
            # Skip if already started
            if language in self.language_servers:
                continue

            if len(server_config.roots) == 0:
                self.logger.log(f"Found server config for {language} that had no roots. No default provided.", logging.INFO)
                continue

            project_root = server_config.roots[0]

            try:
                multilspy_config = MultilspyConfig.from_dict(
                    {"code_language": language.value}
                )

                lsp = SyncLanguageServer.create(
                    multilspy_config, self.logger, project_root
                )

                # Start the server context and keep it alive
                context = lsp.start_server()
                context.__enter__()
                self._server_contexts[language] = context

                self.language_servers[language] = lsp
                self.logger.log(
                    f"Initialized and started language server for {language.value} at {project_root}",
                    logging.INFO,
                )
            except Exception as e:
                self.logger.log(
                    f"Failed to initialize language server for {language.value}: {str(e)}",
                    logging.ERROR,
                )
                raise

    def get_configuration_error_message(self) -> str:
        """
        Get an informative error message for when the runner is not configured.

        Returns:
            Formatted error message with schema instructions.
        """
        return (
            "Language Server Protocol (LSP) is not configured.\n\n"
            "Please create an 'lsp.toml' file in your workspace root with the following schema:\n\n"
            f"{LSP_TOML_SCHEMA}"
        )

    def stop_language_servers(self) -> None:
        """Stop all running language servers."""
        for language in list(self.language_servers.keys()):
            try:
                self.logger.log(
                    f"Stopping language server for {language.value}", logging.INFO
                )
                # Exit the server context
                if language in self._server_contexts:
                    context = self._server_contexts[language]
                    context.__exit__(None, None, None)
                    del self._server_contexts[language]
                del self.language_servers[language]
            except Exception as e:
                self.logger.log(
                    f"Error stopping language server for {language.value}: {str(e)}",
                    logging.ERROR,
                )

    def get_language_server(self, language: Language) -> SyncLanguageServer:
        """
        Get a language server instance.

        Args:
            language: The language to get the server for

        Returns:
            SyncLanguageServer instance

        Raises:
            MCPToolError: If language server not available
        """
        if language not in self.language_servers:
            available = ", ".join(lang.value for lang in self.language_servers.keys())
            raise MCPToolError(
                f"Language server for {language.value} not available. "
                f"Available: {available or 'none'}"
            )
        return self.language_servers[language]

    def create_mcp_server(self) -> Server:
        """
        Create and configure a fastmcp Server instance with LSP tools.

        Returns:
            Configured fastmcp Server ready to serve MCP tools

        Note: Each tool includes fallback configuration checking.
        """
        server = Server("multilspy-mcp")
        self._register_tools(server)
        return server

    def _register_tools(self, server: Server) -> None:
        """
        Register all LSP tools with the fastmcp server.

        Each tool includes a fallback check for configuration at call time.
        Language servers are started once and reused across calls.

        Args:
            server: The fastmcp Server instance
        """

        # Tool: lsp_get_diagnostics
        @server.call_tool()
        async def lsp_get_diagnostics(
            language: str, file_path: Optional[str] = None
        ) -> str:
            """Get diagnostics (errors, warnings) for a file or entire workspace.

            Args:
                language: Programming language (e.g., 'java', 'python')
                file_path: Optional path to specific file
            """
            if not self._ensure_configured():
                return json.dumps(
                    {
                        "status": "error",
                        "message": self.get_configuration_error_message(),
                    }
                )

            try:
                lang = Language(language)
            except (ValueError, KeyError):
                raise MCPToolError(f"Invalid language: {language}")

            lsp = self.get_language_server(lang)

            try:
                if file_path:
                    lsp.open_file(file_path)
                    result = lsp.request_text_document_diagnostics(lsp_types.DocumentDiagnosticParams(textDocument=TextDocumentIdentifier(uri=file_path)))
                else:
                    result = lsp.request_workspace_document_diagnostics(lsp_types.WorkspaceDiagnosticParams(previousResultIds=[]))

                return json.dumps({"status": "success", "diagnostics": result or []})
            except Exception as e:
                raise MCPToolError(f"Failed to get diagnostics: {str(e)}")

        # Tool: lsp_get_definition
        @server.call_tool()
        async def lsp_get_definition(
            language: str, file_path: str, line: int, character: int
        ) -> str:
            """Get the definition of a symbol at a given position.

            Args:
                language: Programming language
                file_path: Path to the file
                line: Line number (0-indexed)
                character: Character position (0-indexed)
            """
            if not self._ensure_configured():
                return json.dumps(
                    {
                        "status": "error",
                        "message": self.get_configuration_error_message(),
                    }
                )

            try:
                lang = Language(language)
            except (ValueError, KeyError):
                raise MCPToolError(f"Invalid language: {language}")

            lsp = self.get_language_server(lang)

            try:
                lsp.open_file(file_path)
                result = lsp.request_definition(file_path, line, character)

                return json.dumps({"status": "success", "definition": result})
            except Exception as e:
                raise MCPToolError(f"Failed to get definition: {str(e)}")

        # Tool: lsp_get_references
        @server.call_tool()
        async def lsp_get_references(
            language: str, file_path: str, line: int, character: int
        ) -> str:
            """Get all references to a symbol.

            Args:
                language: Programming language
                file_path: Path to the file
                line: Line number (0-indexed)
                character: Character position (0-indexed)
            """
            if not self._ensure_configured():
                return json.dumps(
                    {
                        "status": "error",
                        "message": self.get_configuration_error_message(),
                    }
                )

            try:
                lang = Language(language)
            except (ValueError, KeyError):
                raise MCPToolError(f"Invalid language: {language}")

            lsp = self.get_language_server(lang)

            try:
                lsp.open_file(file_path)
                result = lsp.request_references(file_path, line, character)

                return json.dumps({"status": "success", "references": result or []})
            except Exception as e:
                raise MCPToolError(f"Failed to get references: {str(e)}")

        # Tool: lsp_get_hover
        @server.call_tool()
        async def lsp_get_hover(
            language: str, file_path: str, line: int, character: int
        ) -> str:
            """Get hover information for a symbol.

            Args:
                language: Programming language
                file_path: Path to the file
                line: Line number (0-indexed)
                character: Character position (0-indexed)
            """
            if not self._ensure_configured():
                return json.dumps(
                    {
                        "status": "error",
                        "message": self.get_configuration_error_message(),
                    }
                )

            try:
                lang = Language(language)
            except (ValueError, KeyError):
                raise MCPToolError(f"Invalid language: {language}")

            lsp = self.get_language_server(lang)

            try:
                lsp.open_file(file_path)
                result = lsp.request_hover(file_path, line, character)

                return json.dumps({"status": "success", "hover": result})
            except Exception as e:
                raise MCPToolError(f"Failed to get hover information: {str(e)}")

        # Tool: lsp_get_completions
        @server.call_tool()
        async def lsp_get_completions(
            language: str, file_path: str, line: int, character: int
        ) -> str:
            """Get code completions at a specific position.

            Args:
                language: Programming language
                file_path: Path to the file
                line: Line number (0-indexed)
                character: Character position (0-indexed)
            """
            if not self._ensure_configured():
                return json.dumps(
                    {
                        "status": "error",
                        "message": self.get_configuration_error_message(),
                    }
                )

            try:
                lang = Language(language)
            except (ValueError, KeyError):
                raise MCPToolError(f"Invalid language: {language}")

            lsp = self.get_language_server(lang)

            try:
                lsp.open_file(file_path)
                result = lsp.request_completions(file_path, line, character)

                return json.dumps({"status": "success", "completions": result or []})
            except Exception as e:
                raise MCPToolError(f"Failed to get completions: {str(e)}")

        # Tool: lsp_get_document_symbols
        @server.call_tool()
        async def lsp_get_document_symbols(language: str, file_path: str) -> str:
            """Get all symbols in a document (classes, functions, variables, etc.).

            Args:
                language: Programming language
                file_path: Path to the file
            """
            if not self._ensure_configured():
                return json.dumps(
                    {
                        "status": "error",
                        "message": self.get_configuration_error_message(),
                    }
                )

            try:
                lang = Language(language)
            except (ValueError, KeyError):
                raise MCPToolError(f"Invalid language: {language}")

            lsp = self.get_language_server(lang)

            try:
                lsp.open_file(file_path)
                result = lsp.request_document_symbols(file_path)

                return json.dumps({"status": "success", "symbols": result or []})
            except Exception as e:
                raise MCPToolError(f"Failed to get document symbols: {str(e)}")

        # Tool: lsp_get_workspace_symbols
        @server.call_tool()
        async def lsp_get_workspace_symbols(language: str, query: str) -> str:
            """Search for symbols across the entire workspace.

            Args:
                language: Programming language
                query: Symbol name or pattern to search for
            """
            if not self._ensure_configured():
                return json.dumps(
                    {
                        "status": "error",
                        "message": self.get_configuration_error_message(),
                    }
                )

            try:
                lang = Language(language)
            except (ValueError, KeyError):
                raise MCPToolError(f"Invalid language: {language}")

            lsp = self.get_language_server(lang)

            try:
                result = lsp.request_workspace_symbol(query)

                return json.dumps({"status": "success", "symbols": result or []})
            except Exception as e:
                raise MCPToolError(f"Failed to search workspace symbols: {str(e)}")


__all__ = [
    "MCPRunner",
    "LSPConfig",
    "LanguageServerConfig",
    "MCPToolError",
    "LSPNotConfiguredException",
    "LSP_TOML_SCHEMA",
]

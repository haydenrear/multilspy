# MCP Runner for multilspy

The MCP Runner exposes multilspy language servers as tools through the Model Context Protocol (MCP). It allows AI models and other MCP clients to perform code analysis, navigation, and IDE-like features across multiple programming languages.

## Quick Start

### 1. Create Configuration File

Create an `lsp.toml` file in your workspace root:

```toml
[lsp]
language_servers = ["java", "python"]

[lsp.java]
roots = ["/path/to/java/project"]

[lsp.python]
roots = ["/path/to/python/project"]
```

### 2. Initialize the Runner

```python
from multilspy.mcp.mcp_runner import MCPRunner

# Initialize the runner with your workspace root
runner = MCPRunner("/path/to/workspace")

# Start all configured language servers
runner.start_language_servers()

# Get available MCP tools
tools = runner.get_tool_definitions()

# Execute a tool
result = await runner.execute_tool(
    "lsp_get_definitions",
    {
        "language": "java",
        "file_path": "/path/to/file.java",
        "line": 10,
        "character": 5
    }
)

# Clean up
runner.stop_language_servers()
```

## Configuration

### lsp.toml Schema

The `lsp.toml` file uses TOML format and contains language server configurations.

#### Basic Structure

```toml
[lsp]
# List of language servers to start
language_servers = ["java", "python", "rust"]

# Configuration for each language server
[lsp.java]
roots = ["/path/to/java/project"]
java_version = "17"          # Optional
gradle_version = "7.3.3"     # Optional

[lsp.python]
roots = ["/path/to/python/project"]

[lsp.rust]
roots = ["/path/to/rust/project"]
```

#### Supported Languages

- `java` - Eclipse JDTLS
- `python` - Jedi Language Server
- `rust` - Rust Analyzer
- `csharp` - OmniSharp
- `typescript` - TypeScript Language Server
- `javascript` - JavaScript Language Server
- `go` - gopls
- `ruby` - Solargraph
- `dart` - Dart Language Server
- `kotlin` - Kotlin Language Server
- `cpp` - Clangd

#### Multi-Root Projects

You can specify multiple project roots for a single language server:

```toml
[lsp.java]
roots = [
    "/path/to/project1",
    "/path/to/project2",
    "/path/to/project3"
]
```

The first root will be used as the primary workspace root for language server initialization.

### Language-Specific Options

#### Java

```toml
[lsp.java]
roots = ["/path/to/java/project"]
java_version = "17"              # Java version (optional)
gradle_version = "7.3.3"         # Gradle version (optional)
```

#### Python

```toml
[lsp.python]
roots = ["/path/to/python/project"]
```

#### Rust

```toml
[lsp.rust]
roots = ["/path/to/rust/project"]
```

## Available Tools

### 1. lsp_get_diagnostics

Get diagnostics (errors, warnings) for a file or entire workspace.

**Parameters:**
- `language` (required): Programming language
- `file_path` (optional): Path to specific file; if omitted, returns workspace diagnostics

**Example:**
```python
result = await runner.execute_tool("lsp_get_diagnostics", {
    "language": "java",
    "file_path": "/path/to/file.java"
})
```

### 2. lsp_get_definition

Get the definition of a symbol at a given position.

**Parameters:**
- `language` (required): Programming language
- `file_path` (required): Path to the file
- `line` (required): Line number (0-indexed)
- `character` (required): Character position (0-indexed)

**Example:**
```python
result = await runner.execute_tool("lsp_get_definition", {
    "language": "java",
    "file_path": "/path/to/file.java",
    "line": 42,
    "character": 10
})
```

### 3. lsp_get_references

Get all references to a symbol.

**Parameters:**
- `language` (required): Programming language
- `file_path` (required): Path to the file
- `line` (required): Line number (0-indexed)
- `character` (required): Character position (0-indexed)

**Example:**
```python
result = await runner.execute_tool("lsp_get_references", {
    "language": "python",
    "file_path": "/path/to/file.py",
    "line": 15,
    "character": 20
})
```

### 4. lsp_get_hover

Get hover information for a symbol.

**Parameters:**
- `language` (required): Programming language
- `file_path` (required): Path to the file
- `line` (required): Line number (0-indexed)
- `character` (required): Character position (0-indexed)

**Example:**
```python
result = await runner.execute_tool("lsp_get_hover", {
    "language": "rust",
    "file_path": "/path/to/file.rs",
    "line": 5,
    "character": 8
})
```

### 5. lsp_get_completions

Get code completions at a specific position.

**Parameters:**
- `language` (required): Programming language
- `file_path` (required): Path to the file
- `line` (required): Line number (0-indexed)
- `character` (required): Character position (0-indexed)

**Example:**
```python
result = await runner.execute_tool("lsp_get_completions", {
    "language": "typescript",
    "file_path": "/path/to/file.ts",
    "line": 30,
    "character": 15
})
```

### 6. lsp_get_document_symbols

Get all symbols in a document (classes, functions, variables, etc.).

**Parameters:**
- `language` (required): Programming language
- `file_path` (required): Path to the file

**Example:**
```python
result = await runner.execute_tool("lsp_get_document_symbols", {
    "language": "java",
    "file_path": "/path/to/file.java"
})
```

### 7. lsp_get_workspace_symbols

Search for symbols across the entire workspace.

**Parameters:**
- `language` (required): Programming language
- `query` (required): Symbol name or pattern to search for

**Example:**
```python
result = await runner.execute_tool("lsp_get_workspace_symbols", {
    "language": "python",
    "query": "MyClass"
})
```

## Usage Patterns

### Pattern 1: Single Language Analysis

```python
from multilspy.mcp.mcp_runner import MCPRunner

runner = MCPRunner("/path/to/workspace")
runner.start_language_servers()

# Get all symbols in a Java file
symbols = await runner.execute_tool("lsp_get_document_symbols", {
    "language": "java",
    "file_path": "/path/to/Main.java"
})

# Get all references to a method
references = await runner.execute_tool("lsp_get_references", {
    "language": "java",
    "file_path": "/path/to/Main.java",
    "line": 10,
    "character": 5
})

runner.stop_language_servers()
```

### Pattern 2: Multi-Language Workspace

```python
runner = MCPRunner("/path/to/workspace")
runner.start_language_servers()  # Starts both Java and Python servers

# Analyze Java code
java_diags = await runner.execute_tool("lsp_get_diagnostics", {
    "language": "java"
})

# Analyze Python code
python_diags = await runner.execute_tool("lsp_get_diagnostics", {
    "language": "python"
})

runner.stop_language_servers()
```

### Pattern 3: Navigation and Discovery

```python
runner = MCPRunner("/path/to/workspace")
runner.start_language_servers()

# Search for a class
symbols = await runner.execute_tool("lsp_get_workspace_symbols", {
    "language": "java",
    "query": "DatabaseConnection"
})

# Navigate to definition
for symbol in symbols:
    definition = await runner.execute_tool("lsp_get_definition", {
        "language": "java",
        "file_path": symbol["location"]["uri"],
        "line": symbol["location"]["range"]["start"]["line"],
        "character": symbol["location"]["range"]["start"]["character"]
    })

runner.stop_language_servers()
```

## Error Handling

### Configuration Not Found

If `lsp.toml` is not found, the runner will respond with configuration instructions:

```json
{
    "status": "error",
    "message": "Language Server Protocol (LSP) is not configured.\n\nPlease create an 'lsp.toml' file..."
}
```

### Invalid Language

```json
{
    "status": "error",
    "message": "Invalid language: unsupported_lang"
}
```

### Language Server Not Available

```json
{
    "status": "error",
    "message": "Language server for java not available. Available: python, rust"
}
```

### Tool Execution Error

```json
{
    "status": "error",
    "message": "Failed to get definition: File not found"
}
```

## Advanced Configuration

### Environment Variables

You can use environment variables in Python code to set the workspace root:

```python
import os
from multilspy.mcp.mcp_runner import MCPRunner

workspace_root = os.environ.get("WORKSPACE_ROOT", "/default/path")
runner = MCPRunner(workspace_root)
```

### Custom Logger Integration

The MCPRunner uses multilspy's logger. To integrate with your logging system:

```python
from multilspy.mcp.mcp_runner import MCPRunner
from multilspy.multilspy_logger import MultilspyLogger

runner = MCPRunner("/path/to/workspace")
# The runner.logger can be configured as needed
```

### Programmatic Configuration

Instead of `lsp.toml`, you can configure language servers programmatically:

```python
from multilspy.mcp.mcp_runner import MCPRunner, LSPConfig, LanguageServerConfig
from multilspy.multilspy_config import Language

# Create configuration programmatically
config = LSPConfig(
    language_servers=[Language.JAVA, Language.PYTHON],
    servers={
        Language.JAVA: LanguageServerConfig(
            language=Language.JAVA,
            roots=["/path/to/java/project"]
        ),
        Language.PYTHON: LanguageServerConfig(
            language=Language.PYTHON,
            roots=["/path/to/python/project"]
        )
    }
)

# Note: This would require extending MCPRunner to accept programmatic config
# Currently, lsp.toml is the primary configuration method
```

## Performance Considerations

1. **Language Server Startup**: Language servers take time to initialize. The first request may be slow.

2. **File Size Limits**: Large files may take longer to analyze. Some language servers have limits on file size.

3. **Memory Usage**: Multiple language servers consume memory. Consider which servers you actually need.

4. **Workspace Size**: Large workspaces may increase analysis time for workspace-wide operations like symbol search.

## Troubleshooting

### Language Server Fails to Start

**Problem**: "Failed to initialize language server"

**Solutions**:
- Check that required dependencies are installed (Java for Eclipse JDTLS, etc.)
- Verify that project roots in `lsp.toml` are valid directories
- Check that the language is properly installed on your system

### Tools Respond with Configuration Error

**Problem**: All tools return "Language Server Protocol (LSP) is not configured"

**Solutions**:
- Ensure `lsp.toml` exists in the workspace root
- Check `lsp.toml` syntax (valid TOML format)
- Verify that specified language servers are in the `language_servers` list
- Check that all roots in configuration are valid directory paths

### Slow Performance

**Problem**: Tool execution is very slow

**Solutions**:
- Language servers need time to initialize. First requests are slower.
- For large workspaces, workspace-wide operations (symbol search) are slower
- Consider enabling trace logging to identify bottlenecks
- Try analyzing smaller files or more specific regions first

## API Reference

### MCPRunner

Main class for managing language servers and MCP tools.

**Methods:**

- `__init__(workspace_root: Optional[str] = None)` - Initialize runner
- `start_language_servers() -> None` - Start all configured servers
- `stop_language_servers() -> None` - Stop all running servers
- `get_tool_definitions() -> List[Dict[str, Any]]` - Get MCP tool definitions
- `execute_tool(tool_name: str, tool_input: Dict) -> str` - Execute an MCP tool
- `get_language_server(language: Language) -> SyncLanguageServer` - Get specific server

### LSPConfig

Configuration data class for LSP settings.

**Class Methods:**

- `from_dict(config_dict: Dict) -> LSPConfig` - Load from dictionary

**Methods:**

- `to_dict() -> Dict[str, Any]` - Convert to dictionary

### LanguageServerConfig

Configuration for a single language server.

**Attributes:**

- `language: Language` - Programming language
- `roots: List[str]` - Project root directories
- `java_version: Optional[str]` - Java version (Java only)
- `gradle_version: Optional[str]` - Gradle version (Java only)

**Methods:**

- `validate() -> Tuple[bool, Optional[str]]` - Validate configuration

## Examples

See the project repository for complete examples including:
- Basic usage
- Multi-language analysis
- Integration with MCP servers
- Error handling patterns

## Contributing

To extend MCPRunner with new tools or language servers, contribute to the multilspy project.

## License

See the multilspy project for licensing information.
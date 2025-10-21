"""
Pydantic data models for initialize_params.json across all language servers.

This module provides a comprehensive hierarchical model that captures the
LSP (Language Server Protocol) initialize parameters structure.
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field


# ============================================================================
# ClientInfo
# ============================================================================


class ClientInfo(BaseModel):
    """Client information sent during initialization."""

    name: str = Field(..., description="The name of the client")
    version: Optional[str] = Field(None, description="The client version")

    class Config:
        extra = "allow"


# ============================================================================
# Capabilities - Workspace
# ============================================================================


class SymbolKindSupport(BaseModel):
    """Symbol kind support."""

    value_set: Optional[List[int]] = Field(None, alias="valueSet")

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


class TagSupport(BaseModel):
    """Tag support for symbols."""

    value_set: Optional[List[int]] = Field(None, alias="valueSet")

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


class ResolveSupport(BaseModel):
    """Resolve support for workspace symbols."""

    properties: Optional[List[str]] = Field(None)

    class Config:
        extra = "allow"


class SymbolCapability(BaseModel):
    """Workspace symbol capability."""

    dynamic_registration: Optional[bool] = Field(None, alias="dynamicRegistration")
    symbol_kind: Optional[SymbolKindSupport] = Field(None, alias="symbolKind")
    tag_support: Optional[TagSupport] = Field(None, alias="tagSupport")
    resolve_support: Optional[ResolveSupport] = Field(None, alias="resolveSupport")

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


class WorkspaceEditCapability(BaseModel):
    """Workspace edit capability."""

    document_changes: Optional[bool] = Field(None, alias="documentChanges")
    resource_operations: Optional[List[str]] = Field(None, alias="resourceOperations")
    failure_handling: Optional[str] = Field(None, alias="failureHandling")
    normalizes_line_endings: Optional[bool] = Field(None, alias="normalizesLineEndings")
    change_annotation_support: Optional[Dict[str, Any]] = Field(
        None, alias="changeAnnotationSupport"
    )

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


class WorkspaceCapability(BaseModel):
    """Workspace capabilities."""

    apply_edit: Optional[bool] = Field(None, alias="applyEdit")
    workspace_edit: Optional[WorkspaceEditCapability] = Field(
        None, alias="workspaceEdit"
    )
    did_change_configuration: Optional[Dict[str, Any]] = Field(
        None, alias="didChangeConfiguration"
    )
    did_change_watched_files: Optional[Dict[str, Any]] = Field(
        None, alias="didChangeWatchedFiles"
    )
    symbol: Optional[SymbolCapability] = Field(None)
    code_lens: Optional[Dict[str, Any]] = Field(None, alias="codeLens")
    execute_command: Optional[Dict[str, Any]] = Field(None, alias="executeCommand")
    configuration: Optional[Union[bool, Dict[str, Any]]] = Field(None)
    workspace_folders: Optional[bool] = Field(None, alias="workspaceFolders")
    semantic_tokens: Optional[Dict[str, Any]] = Field(None, alias="semanticTokens")
    file_operations: Optional[Dict[str, Any]] = Field(None, alias="fileOperations")
    inline_value: Optional[Dict[str, Any]] = Field(None, alias="inlineValue")
    inlay_hint: Optional[Dict[str, Any]] = Field(None, alias="inlayHint")
    diagnostics: Optional[Dict[str, Any]] = Field(None)

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


# ============================================================================
# Capabilities - TextDocument
# ============================================================================


class CompletionItemCapability(BaseModel):
    """Completion item capability."""

    snippet_support: Optional[bool] = Field(None, alias="snippetSupport")
    commit_characters_support: Optional[bool] = Field(
        None, alias="commitCharactersSupport"
    )
    documentation_format: Optional[List[str]] = Field(None, alias="documentationFormat")
    deprecated_support: Optional[bool] = Field(None, alias="deprecatedSupport")
    preselect_support: Optional[bool] = Field(None, alias="preselectSupport")
    tag_support: Optional[TagSupport] = Field(None, alias="tagSupport")
    insert_replace_support: Optional[bool] = Field(None, alias="insertReplaceSupport")
    resolve_support: Optional[ResolveSupport] = Field(None, alias="resolveSupport")
    insert_text_mode_support: Optional[Dict[str, Any]] = Field(
        None, alias="insertTextModeSupport"
    )
    label_details_support: Optional[bool] = Field(None, alias="labelDetailsSupport")

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


class CompletionCapability(BaseModel):
    """Completion capability."""

    dynamic_registration: Optional[bool] = Field(None, alias="dynamicRegistration")
    context_support: Optional[bool] = Field(None, alias="contextSupport")
    completion_item: Optional[CompletionItemCapability] = Field(
        None, alias="completionItem"
    )
    insert_text_mode: Optional[int] = Field(None, alias="insertTextMode")
    completion_item_kind: Optional[Dict[str, Any]] = Field(
        None, alias="completionItemKind"
    )
    completion_list: Optional[Dict[str, Any]] = Field(None, alias="completionList")

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


class TextDocumentSyncCapability(BaseModel):
    """Text document synchronization capability."""

    dynamic_registration: Optional[bool] = Field(None, alias="dynamicRegistration")
    will_save: Optional[bool] = Field(None, alias="willSave")
    will_save_wait_until: Optional[bool] = Field(None, alias="willSaveWaitUntil")
    did_save: Optional[bool] = Field(None, alias="didSave")

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


class PublishDiagnosticsCapability(BaseModel):
    """Publish diagnostics capability."""

    related_information: Optional[bool] = Field(None, alias="relatedInformation")
    version_support: Optional[bool] = Field(None, alias="versionSupport")
    tag_support: Optional[TagSupport] = Field(None, alias="tagSupport")
    code_description_support: Optional[bool] = Field(
        None, alias="codeDescriptionSupport"
    )
    data_support: Optional[bool] = Field(None, alias="dataSupport")

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


class TextDocumentCapability(BaseModel):
    """Text document capabilities."""

    publish_diagnostics: Optional[PublishDiagnosticsCapability] = Field(
        None, alias="publishDiagnostics"
    )
    synchronization: Optional[TextDocumentSyncCapability] = Field(None)
    completion: Optional[CompletionCapability] = Field(None)
    hover: Optional[Dict[str, Any]] = Field(None)
    signature_help: Optional[Dict[str, Any]] = Field(None, alias="signatureHelp")
    definition: Optional[Dict[str, Any]] = Field(None)
    references: Optional[Dict[str, Any]] = Field(None)
    document_highlight: Optional[Dict[str, Any]] = Field(
        None, alias="documentHighlight"
    )
    document_symbol: Optional[Dict[str, Any]] = Field(None, alias="documentSymbol")
    code_action: Optional[Dict[str, Any]] = Field(None, alias="codeAction")
    code_lens: Optional[Dict[str, Any]] = Field(None, alias="codeLens")
    formatting: Optional[Dict[str, Any]] = Field(None)
    range_formatting: Optional[Dict[str, Any]] = Field(None, alias="rangeFormatting")
    on_type_formatting: Optional[Dict[str, Any]] = Field(None, alias="onTypeFormatting")
    rename: Optional[Dict[str, Any]] = Field(None)
    document_link: Optional[Dict[str, Any]] = Field(None, alias="documentLink")
    type_definition: Optional[Dict[str, Any]] = Field(None, alias="typeDefinition")
    implementation: Optional[Dict[str, Any]] = Field(None)
    color_provider: Optional[Dict[str, Any]] = Field(None, alias="colorProvider")
    folding_range: Optional[Dict[str, Any]] = Field(None, alias="foldingRange")
    declaration: Optional[Dict[str, Any]] = Field(None)
    selection_range: Optional[Dict[str, Any]] = Field(None, alias="selectionRange")
    call_hierarchy: Optional[Dict[str, Any]] = Field(None, alias="callHierarchy")
    semantic_tokens: Optional[Dict[str, Any]] = Field(None, alias="semanticTokens")
    linked_editing_range: Optional[Dict[str, Any]] = Field(
        None, alias="linkedEditingRange"
    )
    type_hierarchy: Optional[Dict[str, Any]] = Field(None, alias="typeHierarchy")
    inline_value: Optional[Dict[str, Any]] = Field(None, alias="inlineValue")
    inlay_hint: Optional[Dict[str, Any]] = Field(None, alias="inlayHint")
    diagnostic: Optional[Dict[str, Any]] = Field(None)

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


# ============================================================================
# Capabilities - Window
# ============================================================================


class WindowCapability(BaseModel):
    """Window capabilities."""

    show_message: Optional[Dict[str, Any]] = Field(None, alias="showMessage")
    show_document: Optional[Dict[str, Any]] = Field(None, alias="showDocument")
    work_done_progress: Optional[bool] = Field(None, alias="workDoneProgress")

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


# ============================================================================
# Capabilities - General
# ============================================================================


class GeneralCapability(BaseModel):
    """General capabilities."""

    stale_request_support: Optional[Dict[str, Any]] = Field(
        None, alias="staleRequestSupport"
    )
    regular_expressions: Optional[Dict[str, Any]] = Field(
        None, alias="regularExpressions"
    )
    markdown: Optional[Dict[str, Any]] = Field(None)
    position_encodings: Optional[List[str]] = Field(None, alias="positionEncodings")

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


# ============================================================================
# Capabilities - NotebookDocument
# ============================================================================


class NotebookDocumentCapability(BaseModel):
    """Notebook document capabilities."""

    synchronization: Optional[Dict[str, Any]] = Field(None)

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


# ============================================================================
# Top-level Capabilities
# ============================================================================


class Capabilities(BaseModel):
    """Client capabilities sent during initialization."""

    workspace: Optional[WorkspaceCapability] = Field(None)
    text_document: Optional[TextDocumentCapability] = Field(None, alias="textDocument")
    window: Optional[WindowCapability] = Field(None)
    general: Optional[GeneralCapability] = Field(None)
    notebook_document: Optional[NotebookDocumentCapability] = Field(
        None, alias="notebookDocument"
    )
    experimental: Optional[Dict[str, Any]] = Field(None)

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


# ============================================================================
# InitializationOptions (language-server specific)
# ============================================================================


class InitializationOptions(BaseModel):
    """Language server specific initialization options. Structure varies by server."""

    class Config:
        extra = "allow"


# ============================================================================
# Top-level InitializeParams
# ============================================================================


class InitializeParamsConfig(BaseModel):
    """
    Complete LSP InitializeParams configuration.

    This is the structure sent by the client to the server during the
    initialize request. While we model the common parts precisely, we
    leave language-server-specific options flexible via extra="allow".
    """

    description: Optional[str] = Field(None, alias="_description")
    process_id: Union[int, str, None] = Field(None, alias="processId")
    client_info: Optional[ClientInfo] = Field(None, alias="clientInfo")
    locale: Optional[str] = Field(None)
    root_path: Optional[str] = Field(None, alias="rootPath")
    root_uri: Optional[str] = Field(None, alias="rootUri")
    capabilities: Optional[Capabilities] = Field(None)
    initialization_options: Optional[Dict[str, Any]] = Field(
        None, alias="initializationOptions"
    )
    trace: Optional[str] = Field(None)
    workspace_folders: Optional[List[Dict[str, Any]]] = Field(
        None, alias="workspaceFolders"
    )

    class Config:
        extra = "allow"
        allow_population_by_field_name = True

    def to_lsp_dict(self) -> Dict[str, Any]:
        """
        Convert to LSP protocol format with camelCase keys.

        Returns:
            Dictionary with camelCase keys suitable for LSP communication
        """
        return self.dict(by_alias=True, exclude_none=False)

    def find_dynamic_substitutions(self) -> List[tuple]:
        """
        Find all fields that appear to require dynamic substitution.

        Looks for string values that contain common placeholder patterns like:
        - Function calls: "os.getpid()", "pathlib.Path(...)"
        - Variable placeholders: "repository_absolute_path"

        Returns:
            List of (path, value) tuples where substitution is needed
        """
        substitutions = []
        self._find_substitutions_recursive(self.dict(), "", substitutions)
        return substitutions

    def _find_substitutions_recursive(
        self, obj: Any, path: str, substitutions: List
    ) -> None:
        """
        Recursively find fields that need dynamic substitution.

        Args:
            obj: Current object to search
            path: Current path in the object tree
            substitutions: Accumulator list for found substitutions
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                self._find_substitutions_recursive(value, new_path, substitutions)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                new_path = f"{path}[{idx}]"
                self._find_substitutions_recursive(item, new_path, substitutions)
        elif isinstance(obj, str):
            # Check for common placeholder patterns
            placeholder_indicators = [
                "os.",
                "pathlib.",
                "repository_absolute_path",
                ".getpid()",
                ".as_uri()",
                "abs(",
            ]
            if any(indicator in obj for indicator in placeholder_indicators):
                substitutions.append((path, obj))

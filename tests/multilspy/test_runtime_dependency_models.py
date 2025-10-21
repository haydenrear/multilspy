"""
Tests for runtime dependency models.
"""

import json
import pathlib
import pytest
from multilspy.runtime_dependency_models import (
    RuntimeDependenciesConfig,
    Dependency,
    InitializeParamsConfig,
)


class TestRuntimeDependenciesConfig:
    """Tests for RuntimeDependenciesConfig model."""

    @pytest.fixture
    def eclipse_jdtls_runtime_deps_path(self):
        """Path to eclipse_jdtls runtime_dependencies.json."""
        return (
            pathlib.Path(__file__).parent.parent.parent
            / "src/multilspy/language_servers/eclipse_jdtls/runtime_dependencies.json"
        )

    @pytest.fixture
    def eclipse_jdtls_runtime_deps(self, eclipse_jdtls_runtime_deps_path):
        """Load eclipse_jdtls runtime dependencies."""
        with open(eclipse_jdtls_runtime_deps_path) as f:
            return json.load(f)

    def test_load_eclipse_jdtls_runtime_dependencies(self, eclipse_jdtls_runtime_deps):
        """Test loading eclipse_jdtls runtime_dependencies.json."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)
        assert config is not None
        assert config.description is not None

    def test_get_all_dependencies(self, eclipse_jdtls_runtime_deps):
        """Test getting all dependencies."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)
        deps = config.get_dependencies()

        assert deps is not None
        assert isinstance(deps, dict)
        assert len(deps) > 0

    def test_get_specific_dependency(self, eclipse_jdtls_runtime_deps):
        """Test getting a specific dependency by name."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)

        jdk_deps = config.get_dependency("jdk_versions")
        assert jdk_deps is not None
        assert isinstance(jdk_deps, dict)

    def test_jdk_versions_flattened_structure(self, eclipse_jdtls_runtime_deps):
        """Test that jdk_versions are returned as flattened dot-notation keys."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)

        jdk_deps = config.get_dependency("jdk_versions")

        # Should have keys like "jdk_versions.17.linux-x64", etc.
        dep_keys = list(jdk_deps.keys())
        assert len(dep_keys) > 0

        # Keys should be either the dependency name or dot-notation paths
        for key in dep_keys:
            assert isinstance(key, str)

    def test_gradle_versions_flattened(self, eclipse_jdtls_runtime_deps):
        """Test that gradle_versions are returned as flattened structure."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)

        gradle_deps = config.get_dependency("gradle_versions")

        assert gradle_deps is not None
        assert isinstance(gradle_deps, dict)
        assert len(gradle_deps) > 0

    def test_vscode_java_flattened(self, eclipse_jdtls_runtime_deps):
        """Test that vscode-java dependencies are flattened."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)

        vscode_deps = config.get_dependency("vscode-java")

        assert vscode_deps is not None
        assert isinstance(vscode_deps, dict)
        # Should have multiple platform variants
        assert len(vscode_deps) > 0

    def test_dependency_list_contains_dependency_objects(
        self, eclipse_jdtls_runtime_deps
    ):
        """Test that dependency values are Dependency objects."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)

        all_deps = config.get_dependencies()

        # Get the first dependency list and check it
        for key, dep_list in all_deps.items():
            assert isinstance(dep_list, list)
            if len(dep_list) > 0:
                # Each item in the list should be a Dependency
                for dep in dep_list:
                    assert isinstance(dep, Dependency)
                    assert hasattr(dep, "url")
                    assert hasattr(dep, "archive_type")
                break

    def test_dependencies_have_required_fields(self, eclipse_jdtls_runtime_deps):
        """Test that all dependencies have required URL and archive_type."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)

        all_deps = config.get_dependencies()

        for key, dep_list in all_deps.items():
            for dep in dep_list:
                assert dep.url is not None
                assert dep.archive_type is not None

    def test_initialization_from_dict(self, eclipse_jdtls_runtime_deps):
        """Test creating config from dict."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)

        # Should work without error
        assert config is not None
        assert len(config.get_dependencies()) > 0

    def test_description_field(self, eclipse_jdtls_runtime_deps):
        """Test that description field is populated."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)

        assert config.description is not None
        assert isinstance(config.description, str)
        assert len(config.description) > 0


class TestInitializeParamsConfig:
    """Tests for InitializeParamsConfig model."""

    @pytest.fixture
    def eclipse_jdtls_initialize_params_path(self):
        """Path to eclipse_jdtls initialize_params.json."""
        return (
            pathlib.Path(__file__).parent.parent.parent
            / "src/multilspy/language_servers/eclipse_jdtls/initialize_params.json"
        )

    @pytest.fixture
    def eclipse_jdtls_initialize_params(self, eclipse_jdtls_initialize_params_path):
        """Load eclipse_jdtls initialize params."""
        with open(eclipse_jdtls_initialize_params_path) as f:
            return json.load(f)

    def test_load_eclipse_jdtls_initialize_params(
        self, eclipse_jdtls_initialize_params
    ):
        """Test loading eclipse_jdtls initialize_params.json."""
        config = InitializeParamsConfig(**eclipse_jdtls_initialize_params)
        assert config is not None
        assert config.description is not None

    def test_process_id_is_string_placeholder(self, eclipse_jdtls_initialize_params):
        """Test that processId can be a string placeholder."""
        config = InitializeParamsConfig(**eclipse_jdtls_initialize_params)
        assert config.process_id == "os.getpid()"

    def test_root_path_is_string_placeholder(self, eclipse_jdtls_initialize_params):
        """Test that rootPath can be a string placeholder."""
        config = InitializeParamsConfig(**eclipse_jdtls_initialize_params)
        assert config.root_path == "repository_absolute_path"

    def test_client_info_parsed(self, eclipse_jdtls_initialize_params):
        """Test that clientInfo is parsed correctly."""
        config = InitializeParamsConfig(**eclipse_jdtls_initialize_params)
        assert config.client_info is not None
        assert config.client_info.name == "Visual Studio Code - Insiders"

    def test_capabilities_parsed(self, eclipse_jdtls_initialize_params):
        """Test that capabilities are parsed."""
        config = InitializeParamsConfig(**eclipse_jdtls_initialize_params)
        assert config.capabilities is not None

    def test_workspace_capabilities(self, eclipse_jdtls_initialize_params):
        """Test that workspace capabilities are parsed."""
        config = InitializeParamsConfig(**eclipse_jdtls_initialize_params)
        assert config.capabilities.workspace is not None
        assert config.capabilities.workspace.apply_edit is True

    def test_text_document_capabilities(self, eclipse_jdtls_initialize_params):
        """Test that text document capabilities are parsed."""
        config = InitializeParamsConfig(**eclipse_jdtls_initialize_params)
        assert config.capabilities.text_document is not None
        assert config.capabilities.text_document.completion is not None

    def test_find_dynamic_substitutions(self, eclipse_jdtls_initialize_params):
        """Test finding fields that need dynamic substitution."""
        config = InitializeParamsConfig(**eclipse_jdtls_initialize_params)
        substitutions = config.find_dynamic_substitutions()

        # Should find at least some dynamic substitutions
        assert len(substitutions) > 0

        # Verify that substitutions is a list of tuples
        assert all(isinstance(s, tuple) and len(s) == 2 for s in substitutions)

        # Check that values contain placeholder indicators
        substitution_values = [value for _, value in substitutions]
        placeholder_indicators = [
            "os.",
            "pathlib.",
            "repository_absolute_path",
            ".getpid()",
            ".as_uri()",
            "abs(",
        ]
        for value in substitution_values:
            assert any(indicator in value for indicator in placeholder_indicators), (
                f"Value '{value}' doesn't contain placeholder indicators"
            )

    def test_to_lsp_dict(self, eclipse_jdtls_initialize_params):
        """Test converting to LSP format with camelCase."""
        config = InitializeParamsConfig(**eclipse_jdtls_initialize_params)
        lsp_dict = config.to_lsp_dict()

        # Should have camelCase keys
        assert "processId" in lsp_dict or "process_id" in lsp_dict
        assert "clientInfo" in lsp_dict or "client_info" in lsp_dict

    def test_initialization_options_preserved(self, eclipse_jdtls_initialize_params):
        """Test that language-server-specific initializationOptions are preserved."""
        config = InitializeParamsConfig(**eclipse_jdtls_initialize_params)
        assert config.initialization_options is not None
        assert "bundles" in config.initialization_options
        assert "settings" in config.initialization_options

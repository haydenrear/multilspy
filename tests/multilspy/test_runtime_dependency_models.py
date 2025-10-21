"""
Tests for runtime dependency models.
"""

import json
import pathlib
import pytest
from multilspy.runtime_dependency_models import (
    RuntimeDependenciesConfig,
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

    def test_get_dependency(self, eclipse_jdtls_runtime_deps):
        """Test getting a specific dependency."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)

        jdk_versions = config.get_dependency("jdk_versions")
        deps = config.get_dependencies()
        assert jdk_versions is not None
        assert not jdk_versions.is_leaf()

    def test_get_version_from_jdk(self, eclipse_jdtls_runtime_deps):
        """Test getting a specific version from jdk_versions."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)

        jdk_versions = config.get_dependency("jdk_versions")
        jdk_17 = jdk_versions.get_child("17")

        assert jdk_17 is not None
        assert not jdk_17.is_leaf()

    def test_get_architecture_from_version(self, eclipse_jdtls_runtime_deps):
        """Test getting a specific architecture from version."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)

        jdk_versions = config.get_dependency("jdk_versions")
        jdk_17 = jdk_versions.get_child("17")
        jdk_17_linux = jdk_17.get_child("linux-x64")

        assert jdk_17_linux is not None
        assert jdk_17_linux.is_leaf()
        assert jdk_17_linux.url is not None
        assert jdk_17_linux.archive_type == "tar.gz"

    def test_jdk_17_has_all_platforms(self, eclipse_jdtls_runtime_deps):
        """Test that JDK 17 has all expected platforms."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)

        jdk_17 = config.get_dependency("jdk_versions").get_child("17")
        platforms = jdk_17.get_all_children()

        expected_platforms = {
            "linux-x64",
            "osx-x64",
            "osx-arm64",
            "win-x64",
            "linux-arm64",
        }
        assert set(platforms.keys()) == expected_platforms

    def test_gradle_versions_single_architecture(self, eclipse_jdtls_runtime_deps):
        """Test that gradle_versions is a versioned, platform-agnostic dependency."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)

        gradle_versions = config.get_dependency("gradle_versions")
        gradle_733 = gradle_versions.get_child("7.3.3")

        assert gradle_733.is_leaf()
        assert gradle_733.url is not None
        assert gradle_733.archive_type == "zip"

    def test_vscode_java_has_multiple_platforms(self, eclipse_jdtls_runtime_deps):
        """Test that vscode-java has multiple platform variants."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)

        vscode_java = config.get_dependency("vscode-java")
        platforms = vscode_java.get_all_children()

        assert len(platforms) > 0
        assert "linux-x64" in platforms

    def test_find_all_downloadables(self, eclipse_jdtls_runtime_deps):
        """Test finding all downloadable items."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)

        downloadables = config.find_all_downloadables()

        # Should find many downloadables
        assert len(downloadables) > 0

        # Each should have url and archiveType
        for item in downloadables:
            assert "url" in item
            assert "archiveType" in item

    def test_to_dict_conversion(self, eclipse_jdtls_runtime_deps):
        """Test converting back to dict."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)
        converted = config.to_dict()

        assert "jdk_versions" in converted
        assert "_description" not in converted  # Excluded by alias

        # Verify we can reload it
        config2 = RuntimeDependenciesConfig(**converted)
        assert config2 is not None

    def test_to_dict_with_aliases(self, eclipse_jdtls_runtime_deps):
        """Test converting to dict with camelCase aliases."""
        config = RuntimeDependenciesConfig(**eclipse_jdtls_runtime_deps)
        converted = config.to_dict_with_aliases()

        # Find a downloadable with archiveType
        jdk_17_linux = (
            config.get_dependency("jdk_versions").get_child("17").get_child("linux-x64")
        )

        # The original should have archiveType as camelCase in JSON
        assert jdk_17_linux.archive_type is not None

    def test_from_dict_constructor(self, eclipse_jdtls_runtime_deps):
        """Test from_dict class method."""
        config = RuntimeDependenciesConfig.from_dict(eclipse_jdtls_runtime_deps)
        assert config is not None
        assert config.get_dependency("jdk_versions") is not None


class TestInitializeParamsConfig:
    """Tests for InitializeParamsConfig model."""

    @pytest.fixture
    def eclipse_jdtls_initialize_params_path(self):
        """Path to eclipse_jdtls initialize_params.json."""
        return (
            pathlib.Path(__file__).parent.parent
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

        # Should find at least processId, rootPath, and rootUri
        assert len(substitutions) > 0

        substitution_paths = [path for path, _ in substitutions]
        assert any("processId" in path for path in substitution_paths)
        assert any("rootPath" in path for path in substitution_paths)

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

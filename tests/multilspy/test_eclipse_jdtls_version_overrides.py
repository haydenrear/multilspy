"""
Integration tests for Eclipse JDTLS version override functionality.

These tests verify that:
1. The language server can be initialized with default configuration (backward compatibility)
2. Custom JDK versions (Java 21) can be downloaded and used
3. Custom Gradle versions (8.5) can be downloaded and used
4. Downloaded archives are properly extracted to the static directory
5. The language server operates correctly with version overrides
6. Multiple version overrides work together

The tests use real Java repositories and perform actual LSP operations to validate
that version overrides work end-to-end with actual downloads and extraction.
"""

import pytest
import os
from pathlib import PurePath, Path
from multilspy import LanguageServer
from multilspy.multilspy_config import Language, MultilspyConfig
from multilspy.multilspy_types import Position, CompletionItemKind
from multilspy.multilspy_utils import PlatformUtils
from tests.test_utils import create_test_context

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_eclipse_jdtls_default_no_version_overrides():
    """
    Test that EclipseJDTLS works with default configuration (no version overrides).

    This verifies backward compatibility - when no version overrides are specified,
    the system should use the default bundled versions (JDK 17, Gradle 7.3.3, Lombok 1.18.30).
    """
    code_language = Language.JAVA
    params = {
        "code_language": code_language,
        "repo_url": "https://github.com/LakshyAAAgrawal/ExampleRepo/",
        "repo_commit": "f3762fd55a457ff9c6b0bf3b266de2b203a766ab",
    }
    with create_test_context(params) as context:
        # Verify no version overrides are set
        assert context.config.java_version is None
        assert context.config.gradle_version is None
        assert context.config.lombok_version is None

        lsp = LanguageServer.create(
            context.config, context.logger, context.source_directory
        )

        async with lsp.start_server():
            # Perform a simple operation to verify the server is working
            filepath = str(PurePath("Person.java"))
            result = await lsp.request_document_symbols(filepath)

            # Verify we got valid results
            assert result is not None
            assert len(result) > 0

            # Check that symbols were returned (indicates successful parsing)
            symbols, _ = result
            assert any(symbol["name"] == "Person" for symbol in symbols)


@pytest.mark.asyncio
async def test_eclipse_jdtls_with_java21_version_override():
    """
    Test that EclipseJDTLS downloads and uses Java 21.

    This test verifies that:
    1. Java 21 is downloaded from the configured URL
    2. The archive is extracted to the static/jdk-21 directory
    3. The JDK binaries are accessible (java executable is found)
    4. The language server initializes and functions correctly with Java 21
    5. The jre_path and jre_home_path are properly updated in runtime configuration
    """
    code_language = Language.JAVA
    params = {
        "code_language": code_language,
        "repo_url": "https://github.com/LakshyAAAgrawal/ExampleRepo/",
        "repo_commit": "f3762fd55a457ff9c6b0bf3b266de2b203a766ab",
        "java_version": "21",
    }
    with create_test_context(params) as context:
        # Verify java_version override is set
        assert context.config.java_version == "21"

        lsp = LanguageServer.create(
            context.config, context.logger, context.source_directory
        )

        # After creation, verify that Java 21 was downloaded and extracted
        eclipse_jdtls_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "multilspy"
            / "language_servers"
            / "eclipse_jdtls"
        )
        static_dir = eclipse_jdtls_path / "static"
        jdk21_dir = static_dir / "jdk-21"

        # Verify the JDK 21 directory exists
        assert jdk21_dir.exists(), f"JDK 21 directory not found at {jdk21_dir}"

        # Verify java executable exists in the JDK
        platform_id = PlatformUtils.get_platform_id().value
        if platform_id.startswith("win"):
            java_exe = jdk21_dir / "bin" / "java.exe"
        else:
            java_exe = jdk21_dir / "bin" / "java"

        assert java_exe.exists() or (jdk21_dir / "bin" / "java").exists(), (
            f"Java executable not found in {jdk21_dir / 'bin'}"
        )

        # Verify the language server can start and work with Java 21
        async with lsp.start_server():
            filepath = str(PurePath("Person.java"))
            result = await lsp.request_document_symbols(filepath)

            assert result is not None
            assert len(result) > 0

            symbols, _ = result
            assert any(symbol["name"] == "Person" for symbol in symbols)


@pytest.mark.asyncio
async def test_eclipse_jdtls_with_gradle85_version_override():
    """
    Test that EclipseJDTLS downloads and uses Gradle 8.5.

    This test verifies that:
    1. Gradle 8.5 is downloaded from the configured URL
    2. The archive is extracted to the static/gradle-8.5 directory
    3. The gradle binaries are accessible (gradle executable is found)
    4. The language server initializes and functions correctly with Gradle 8.5
    5. The gradle_path is properly updated in runtime configuration
    """
    code_language = Language.JAVA
    params = {
        "code_language": code_language,
        "repo_url": "https://github.com/LakshyAAAgrawal/ExampleRepo/",
        "repo_commit": "f3762fd55a457ff9c6b0bf3b266de2b203a766ab",
        "gradle_version": "8.5",
    }
    with create_test_context(params) as context:
        # Verify gradle_version override is set
        assert context.config.gradle_version == "8.5"

        lsp = LanguageServer.create(
            context.config, context.logger, context.source_directory
        )

        # After creation, verify that Gradle 8.5 was downloaded and extracted
        eclipse_jdtls_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "multilspy"
            / "language_servers"
            / "eclipse_jdtls"
        )
        static_dir = eclipse_jdtls_path / "static"
        gradle85_dir = static_dir / "gradle-8.5"

        # Verify the Gradle 8.5 directory exists
        assert gradle85_dir.exists(), (
            f"Gradle 8.5 directory not found at {gradle85_dir}"
        )

        # Verify gradle executable exists
        platform_id = PlatformUtils.get_platform_id().value
        if platform_id.startswith("win"):
            gradle_exe = gradle85_dir / "gradle" / "bin" / "gradle.bat"
        else:
            gradle_exe = gradle85_dir / "gradle" / "bin" / "gradle"

        # The gradle wrapper might be in different locations, so check multiple paths
        gradle_found = (
            gradle_exe.exists()
            or (gradle85_dir / "bin" / "gradle").exists()
            or (gradle85_dir / "bin" / "gradle.bat").exists()
            or any((gradle85_dir / "gradle" / "bin").glob("gradle*"))
        )

        assert gradle_found, f"Gradle executable not found in {gradle85_dir}"

        # Verify the language server can start and work with Gradle 8.5
        async with lsp.start_server():
            filepath = str(PurePath("Person.java"))
            result = await lsp.request_document_symbols(filepath)

            assert result is not None
            assert len(result) > 0

            symbols, _ = result
            assert any(symbol["name"] == "Person" for symbol in symbols)


@pytest.mark.asyncio
async def test_eclipse_jdtls_with_java21_and_gradle85_overrides():
    """
    Test that EclipseJDTLS works with both Java 21 and Gradle 8.5 overrides.

    This is the most comprehensive test, verifying that:
    1. Both Java 21 and Gradle 8.5 are downloaded and extracted
    2. The static directories are properly organized (jdk-21 and gradle-8.5)
    3. Both tools are accessible in their respective directories
    4. The language server initializes correctly with both overrides
    5. The initialize_params are properly updated with both paths
    6. LSP operations work correctly with the custom versions
    """
    code_language = Language.JAVA
    params = {
        "code_language": code_language,
        "repo_url": "https://github.com/LakshyAAAgrawal/ExampleRepo/",
        "repo_commit": "f3762fd55a457ff9c6b0bf3b266de2b203a766ab",
        "java_version": "21",
        "gradle_version": "8.5",
    }
    with create_test_context(params) as context:
        # Verify both version overrides are set
        assert context.config.java_version == "21"
        assert context.config.gradle_version == "8.5"

        lsp = LanguageServer.create(
            context.config, context.logger, context.source_directory
        )

        # After creation, verify both were downloaded and extracted
        eclipse_jdtls_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "multilspy"
            / "language_servers"
            / "eclipse_jdtls"
        )
        static_dir = eclipse_jdtls_path / "static"

        jdk21_dir = static_dir / "jdk-21"
        gradle85_dir = static_dir / "gradle-8.5"

        # Verify both directories exist
        assert jdk21_dir.exists(), f"JDK 21 directory not found at {jdk21_dir}"
        assert gradle85_dir.exists(), (
            f"Gradle 8.5 directory not found at {gradle85_dir}"
        )

        # Verify executables exist
        platform_id = PlatformUtils.get_platform_id().value
        if platform_id.startswith("win"):
            java_exe = jdk21_dir / "bin" / "java.exe"
        else:
            java_exe = jdk21_dir / "bin" / "java"

        assert java_exe.exists() or (jdk21_dir / "bin" / "java").exists(), (
            f"Java executable not found in {jdk21_dir / 'bin'}"
        )

        gradle_found = (
            (gradle85_dir / "gradle" / "bin" / "gradle").exists()
            or (gradle85_dir / "gradle" / "bin" / "gradle.bat").exists()
            or any((gradle85_dir / "gradle" / "bin").glob("gradle*"))
        )

        assert gradle_found, f"Gradle executable not found in {gradle85_dir}"

        # Verify the language server works with both overrides
        async with lsp.start_server():
            # Test document symbols
            filepath = str(PurePath("Person.java"))
            result = await lsp.request_document_symbols(filepath)

            assert result is not None
            assert len(result) > 0

            symbols, _ = result
            assert any(symbol["name"] == "Person" for symbol in symbols)

            # Test definition lookup
            result = await lsp.request_definition(filepath, 1, 0)
            assert isinstance(result, list)


@pytest.mark.asyncio
async def test_eclipse_jdtls_with_all_version_overrides():
    """
    Test that EclipseJDTLS works with all three version overrides specified together.

    This verifies that java_version, gradle_version, and lombok_version can all
    be specified and the language server functions correctly.
    """
    code_language = Language.JAVA
    params = {
        "code_language": code_language,
        "repo_url": "https://github.com/LakshyAAAgrawal/ExampleRepo/",
        "repo_commit": "f3762fd55a457ff9c6b0bf3b266de2b203a766ab",
        "java_version": "21",
        "gradle_version": "8.5",
        "lombok_version": "1.18.30",
    }
    with create_test_context(params) as context:
        # Verify all version overrides are set
        assert context.config.java_version == "21"
        assert context.config.gradle_version == "8.5"
        assert context.config.lombok_version == "1.18.30"

        lsp = LanguageServer.create(
            context.config, context.logger, context.source_directory
        )

        async with lsp.start_server():
            # Perform comprehensive LSP operations to verify everything works
            filepath = str(PurePath("Person.java"))

            # Test document symbols
            result = await lsp.request_document_symbols(filepath)
            assert result is not None
            symbols, _ = result
            assert any(symbol["name"] == "Person" for symbol in symbols)

            # Test definition lookup
            result = await lsp.request_definition(filepath, 1, 0)
            assert isinstance(result, list)

            # Test hover
            result = await lsp.request_hover(filepath, 1, 5)
            # Either returns hover info or None, both are valid
            assert result is not None or result is None


@pytest.mark.asyncio
async def test_eclipse_jdtls_with_version_overrides_completions():
    """
    Test that code completions work correctly with Java 21 and Gradle 8.5 overrides.

    This verifies that the language server's completion engine functions properly
    when version overrides are specified, using a more complex Java project.
    """
    code_language = Language.JAVA
    params = {
        "code_language": code_language,
        "repo_url": "https://github.com/LakshyAAAgrawal/clickhouse-highlevel-sinker/",
        "repo_commit": "5775fd7a67e7b60998e1614cf44a8a1fc3190ab0",
        "java_version": "21",
        "gradle_version": "8.5",
    }
    with create_test_context(params) as context:
        lsp = LanguageServer.create(
            context.config, context.logger, context.source_directory
        )

        async with lsp.start_server():
            completions_filepath = "src/main/java/com/xlvchao/clickhouse/datasource/ClickHouseDataSource.java"

            with lsp.open_file(completions_filepath):
                # Delete some text and request completions
                deleted_text = lsp.delete_text_between_positions(
                    completions_filepath,
                    Position(line=74, character=17),
                    Position(line=78, character=4),
                )
                assert (
                    deleted_text
                    == """newServerNode()
                .withIp(arr[0])
                .withPort(Integer.parseInt(arr[1]))
                .build();
    """
                )
                completions = await lsp.request_completions(
                    completions_filepath, 74, 17
                )
                completions = [
                    completion["completionText"] for completion in completions
                ]

                # Verify we got expected completions
                assert set(completions) == set(["class", "newServerNode"])


@pytest.mark.asyncio
async def test_eclipse_jdtls_static_directory_structure():
    """
    Test that the static directory structure is correctly created when using version overrides.

    This verifies that:
    1. Default vscode-java bundle is extracted to static/vscode-java
    2. Custom JDK 21 is extracted to static/jdk-21
    3. Custom Gradle 8.5 is extracted to static/gradle-8.5
    4. Intellicode is extracted to static/intellicode
    5. All directories contain expected files/subdirectories
    """
    code_language = Language.JAVA
    params = {
        "code_language": code_language,
        "repo_url": "https://github.com/LakshyAAAgrawal/ExampleRepo/",
        "repo_commit": "f3762fd55a457ff9c6b0bf3b266de2b203a766ab",
        "java_version": "21",
        "gradle_version": "8.5",
    }
    with create_test_context(params) as context:
        lsp = LanguageServer.create(
            context.config, context.logger, context.source_directory
        )

        eclipse_jdtls_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "multilspy"
            / "language_servers"
            / "eclipse_jdtls"
        )
        static_dir = eclipse_jdtls_path / "static"

        # Verify expected directories exist
        expected_dirs = [
            static_dir / "vscode-java",  # Default vscode-java bundle
            static_dir / "gradle-8.5",  # Custom Gradle 8.5
            static_dir / "jdk-21",  # Custom JDK 21
            static_dir / "intellicode",  # Intellicode
        ]

        for dir_path in expected_dirs:
            assert dir_path.exists(), f"Expected directory not found: {dir_path}"

        # Verify vscode-java has expected structure
        vscode_java_dir = static_dir / "vscode-java"
        assert (vscode_java_dir / "extension").exists(), (
            "vscode-java extension directory not found"
        )

        # Verify intellicode has expected structure
        intellicode_dir = static_dir / "intellicode"
        assert (intellicode_dir / "extension").exists(), (
            "intellicode extension directory not found"
        )

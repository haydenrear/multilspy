"""
Provides Java specific instantiation of the LanguageServer class. Contains various configurations and settings specific to Java.
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union
import dataclasses
import json
import logging
import os
import pathlib
import shutil
import stat
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from multilspy.multilspy_logger import MultilspyLogger
from multilspy.language_server import LanguageServer
from multilspy.lsp_protocol_handler.server import ProcessLaunchInfo
from multilspy.lsp_protocol_handler.lsp_types import InitializeParams
from multilspy.multilspy_config import MultilspyConfig
from multilspy.multilspy_settings import MultilspySettings
from multilspy.multilspy_utils import FileUtils
from multilspy.multilspy_utils import PlatformUtils
from multilspy.runtime_dependency_config.config_manager import DependencyState
from multilspy.runtime_dependency_models import (
    RuntimeDependenciesConfig,
    InitializeParamsConfig,
)
from multilspy.runtime_dependency_config import DependencyConfigManager
from multilspy.runtime_dependency_downloader import DependencyDownloader
from pathlib import PurePath


@dataclasses.dataclass
class RuntimeDependencyPaths:
    """
    Stores the paths to the runtime dependencies of EclipseJDTLS
    """

    gradle_path: str
    lombok_jar_path: str
    jre_path: str
    jre_home_path: str
    jdtls_launcher_jar_path: str
    jdtls_readonly_config_path: str
    intellicode_jar_path: str
    intellisense_members_path: str


class EclipseJDTLS(LanguageServer):
    """
    The EclipseJDTLS class provides a Java specific implementation of the LanguageServer class
    """

    def __init__(
        self,
        config: MultilspyConfig,
        logger: MultilspyLogger,
        repository_root_path: str,
    ):
        """
        Creates a new EclipseJDTLS instance initializing the language server settings appropriately.
        This class is not meant to be instantiated directly. Use LanguageServer.create() instead.
        """

        self.config = config
        runtime_dependency_paths = self.setupRuntimeDependencies(logger, config)
        self.runtime_dependency_paths = runtime_dependency_paths

        # ws_dir is the workspace directory for the EclipseJDTLS server
        ws_dir = str(
            PurePath(
                MultilspySettings.get_language_server_directory(),
                "EclipseJDTLS",
                "workspaces",
                uuid.uuid4().hex,
            )
        )

        # shared_cache_location is the global cache used by Eclipse JDTLS across all workspaces
        shared_cache_location = str(
            PurePath(
                MultilspySettings.get_global_cache_directory(),
                "lsp",
                "EclipseJDTLS",
                "sharedIndex",
            )
        )

        jre_path = self.runtime_dependency_paths.jre_path
        lombok_jar_path = self.runtime_dependency_paths.lombok_jar_path

        jdtls_launcher_jar = self.runtime_dependency_paths.jdtls_launcher_jar_path

        os.makedirs(ws_dir, exist_ok=True)

        data_dir = str(PurePath(ws_dir, "data_dir"))
        jdtls_config_path = str(PurePath(ws_dir, "config_path"))

        jdtls_readonly_config_path = (
            self.runtime_dependency_paths.jdtls_readonly_config_path
        )

        if not os.path.exists(jdtls_config_path):
            shutil.copytree(jdtls_readonly_config_path, jdtls_config_path)

        for static_path in [
            jre_path,
            lombok_jar_path,
            jdtls_launcher_jar,
            jdtls_config_path,
            jdtls_readonly_config_path,
        ]:
            assert os.path.exists(static_path), static_path

        # TODO: Add "self.runtime_dependency_paths.jre_home_path"/bin to $PATH as well
        proc_env = {
            "syntaxserver": "false",
            "JAVA_HOME": self.runtime_dependency_paths.jre_home_path,
        }
        proc_cwd = repository_root_path
        cmd = " ".join(
            [
                jre_path,
                "--add-modules=ALL-SYSTEM",
                "--add-opens",
                "java.base/java.util=ALL-UNNAMED",
                "--add-opens",
                "java.base/java.lang=ALL-UNNAMED",
                "--add-opens",
                "java.base/sun.nio.fs=ALL-UNNAMED",
                "-Declipse.application=org.eclipse.jdt.ls.core.id1",
                "-Dosgi.bundles.defaultStartLevel=4",
                "-Declipse.product=org.eclipse.jdt.ls.core.product",
                "-Djava.import.generatesMetadataFilesAtProjectRoot=false",
                "-Dfile.encoding=utf8",
                "-noverify",
                "-XX:+UseParallelGC",
                "-XX:GCTimeRatio=4",
                "-XX:AdaptiveSizePolicyWeight=90",
                "-Dsun.zip.disableMemoryMapping=true",
                "-Djava.lsp.joinOnCompletion=true",
                "-Xmx3G",
                "-Xms100m",
                "-Xlog:disable",
                "-Dlog.level=ALL",
                f"-javaagent:{lombok_jar_path}",
                f"-Djdt.core.sharedIndexLocation={shared_cache_location}",
                "-jar",
                jdtls_launcher_jar,
                "-configuration",
                jdtls_config_path,
                "-data",
                data_dir,
            ]
        )

        self.service_ready_event = asyncio.Event()
        self.intellicode_enable_command_available = asyncio.Event()
        self.initialize_searcher_command_available = asyncio.Event()

        super().__init__(
            config,
            logger,
            repository_root_path,
            ProcessLaunchInfo(cmd, proc_env, proc_cwd),
            "java",
        )

    def setupRuntimeDependencies(
        self, logger: MultilspyLogger, config: MultilspyConfig
    ) -> RuntimeDependencyPaths:
        """
        Setup runtime dependencies for EclipseJDTLS using the modular dependency management system.

        This method:
        1. Loads runtime_dependencies.json into a Pydantic model
        2. Creates a DependencyConfigManager to plan which dependencies to download
        3. Creates a DependencyDownloader to execute the downloads
        4. Maps downloaded files to RuntimeDependencyPaths
        """
        # Get base directory for storing static dependencies
        base_static_dir = str(
            PurePath(os.path.abspath(os.path.dirname(__file__)), "static")
        )
        os.makedirs(base_static_dir, exist_ok=True)

        # Load runtime dependencies JSON
        with open(
            str(PurePath(os.path.dirname(__file__), "runtime_dependencies.json")), "r"
        ) as f:
            runtime_deps_data = json.load(f)

        # Parse into Pydantic model
        runtime_deps_config = RuntimeDependenciesConfig(**runtime_deps_data)

        # Create configuration manager
        config_manager = DependencyConfigManager(
            runtime_deps_config=runtime_deps_config,
            multilspy_config=config,
            base_download_path=base_static_dir,
        )

        # Create download plans
        config_manager.create_download_plan()

        # Create downloader and execute downloads
        downloader = DependencyDownloader(config_manager, logger)
        success = downloader.download_all_pending()

        if not success:
            logger.log(
                "Some runtime dependencies failed to download. Check logs for details.",
                logging.ERROR,
            )

        # Get download summary
        summary = downloader.get_download_summary()
        logger.log(
            f"Download summary: {summary['completed']} completed, "
            f"{summary['failed']} failed, {summary['pending']} pending",
            logging.INFO,
        )

        # Extract paths from downloaded dependencies
        return self._extract_dependency_paths(
            base_static_dir,
            runtime_deps_config,
            config_manager,
            logger,
        )

    def _extract_dependency_paths(
        self,
        base_dir: str,
        runtime_deps_config: RuntimeDependenciesConfig,
        config_manager: DependencyConfigManager,
        logger: MultilspyLogger,
    ) -> RuntimeDependencyPaths:
        """
        Extract the paths to required dependencies from the downloaded files.

        Args:
            base_dir: Base directory where dependencies are stored
            runtime_deps_config: The loaded runtime dependencies configuration
            config_manager: The configuration manager with download states
            logger: Logger for messages

        Returns:
            RuntimeDependencyPaths with all required paths
        """
        platform_id = PlatformUtils.get_platform_id()

        # Helper function to get extra field from RuntimeDependency
        def get_extra_field(dep_dict: dict, field_name: str, default: str = "") -> str:
            """Extract extra field from Pydantic model dict."""
            # First try direct access (for Pydantic extra fields)
            if field_name in dep_dict:
                return str(dep_dict[field_name])
            return default

        # Extract vscode-java paths
        vscode_java_state = self._get_dependency_state(config_manager, "vscode-java")

        if not vscode_java_state or not vscode_java_state.is_downloaded():
            raise RuntimeError("vscode-java dependency was not downloaded successfully")

        vscode_java_path = vscode_java_state.downloaded_path

        # Extract gradle paths
        gradle_version = self.config.gradle_version or "7.3.3"
        gradle_state = self._get_dependency_state(config_manager, f"gradle_versions.{gradle_version}")

        if not gradle_state or not gradle_state.is_downloaded():
            raise RuntimeError(
                f"Gradle {gradle_version} was not downloaded successfully"
            )

        gradle_path = gradle_state.downloaded_path

        # Get vscode-java metadata for relative paths
        # Navigate through the dependencies structure: dependencies.vscode-java[platform_id]
        vscode_java_dict = runtime_deps_config.__dict__.get("dependencies", {})
        if isinstance(vscode_java_dict, dict):
            vscode_java_dict = vscode_java_dict.get("vscode-java", {})
            if isinstance(vscode_java_dict, dict):
                vscode_java_meta_dict = vscode_java_dict.get(platform_id.value, {})
            else:
                vscode_java_meta_dict = {}
        else:
            vscode_java_meta_dict = {}

        if not vscode_java_meta_dict:
            raise RuntimeError(
                f"No metadata found for vscode-java on platform {platform_id.value}"
            )

        # Extract relative paths from metadata
        jre_home_path = str(
            PurePath(
                vscode_java_path,
                get_extra_field(vscode_java_meta_dict, "jre_home_path"),
            )
        )
        jre_path = str(
            PurePath(
                vscode_java_path, get_extra_field(vscode_java_meta_dict, "jre_path")
            )
        )
        lombok_jar_path = str(
            PurePath(
                vscode_java_path,
                get_extra_field(vscode_java_meta_dict, "lombok_jar_path"),
            )
        )
        jdtls_launcher_jar_path = str(
            PurePath(
                vscode_java_path,
                get_extra_field(vscode_java_meta_dict, "jdtls_launcher_jar_path"),
            )
        )
        jdtls_readonly_config_path = str(
            PurePath(
                vscode_java_path,
                get_extra_field(vscode_java_meta_dict, "jdtls_readonly_config_path"),
            )
        )

        # Handle custom JDK if specified
        if self.config.java_version:
            jdk_state = self._get_dependency_state(config_manager, f"jdk_versions.{self.config.java_version}.{platform_id.value}")

            if jdk_state and jdk_state.is_downloaded():
                jdk_path = jdk_state.downloaded_path

                jdk_meta_dict = runtime_deps_config.get_dependency(jdk_state.dependency_key)

                if jdk_meta_dict:
                    jre_home_path = str(
                        PurePath(
                            jdk_path, get_extra_field(jdk_meta_dict, "jre_home_path")))
                    jre_path = str(
                        PurePath(jdk_path, get_extra_field(jdk_meta_dict, "jre_path")))

        intellicode_state = self._get_dependency_state(config_manager, "intellicode")

        if not intellicode_state or not intellicode_state.is_downloaded():
            raise RuntimeError("Intellicode dependency was not downloaded successfully")

        intellicode_path = intellicode_state.downloaded_path
        intellicode_meta_dict = runtime_deps_config.get_dependency(intellicode_state.dependency_key)

        if not intellicode_meta_dict:
            raise RuntimeError("No metadata found for intellicode")

        intellicode_jar_path = str(
            PurePath(
                intellicode_path,
                get_extra_field(intellicode_meta_dict, "intellicode_jar_path"),))
        intellisense_members_path = str(
            PurePath(
                intellicode_path,
                get_extra_field(intellicode_meta_dict, "intellisense_members_path"),))

        # Make jre_path executable
        if os.path.exists(jre_path):
            os.chmod(jre_path, stat.S_IEXEC)

        logger.log(
            f"Runtime dependencies resolved: JRE at {jre_home_path}",
            logging.INFO,
        )

        return RuntimeDependencyPaths(
            gradle_path=gradle_path,
            lombok_jar_path=lombok_jar_path,
            jre_path=jre_path,
            jre_home_path=jre_home_path,
            jdtls_launcher_jar_path=jdtls_launcher_jar_path,
            jdtls_readonly_config_path=jdtls_readonly_config_path,
            intellicode_jar_path=intellicode_jar_path,
            intellisense_members_path=intellisense_members_path,
        )

    @staticmethod
    def _get_dependency_state(config_manager: DependencyConfigManager, name: str) -> DependencyState:
        # Extract intellicode paths
        intellicode_deps = config_manager.get_dependency(name)
        intellicode_state = None
        for key, state in intellicode_deps.items():
            if name in key:
                intellicode_state = state
                break
        return intellicode_state

    def _get_initialize_params(self, repository_absolute_path: str) -> InitializeParams:
        """
        Returns the initialize parameters for the EclipseJDTLS server.

        Uses the InitializeParamsConfig Pydantic model to load and validate the JSON,
        then substitutes dynamic values (repository path, JDK path, gradle path, etc.)
        and returns the initialized parameters as a dictionary.
        """
        # Look into https://github.com/eclipse/eclipse.jdt.ls/blob/master/org.eclipse.jdt.ls.core/src/org/eclipse/jdt/ls/core/internal/preferences/Preferences.java to understand all the options available
        with open(
            str(PurePath(os.path.dirname(__file__), "initialize_params.json")), "r"
        ) as f:
            init_params_data = json.load(f)

        # Parse into Pydantic model for validation
        init_params_config = InitializeParamsConfig(**init_params_data)

        if not os.path.isabs(repository_absolute_path):
            repository_absolute_path = os.path.abspath(repository_absolute_path)

        # Substitute dynamic top-level values
        init_params_config.process_id = os.getpid()
        init_params_config.root_path = repository_absolute_path
        init_params_config.root_uri = pathlib.Path(repository_absolute_path).as_uri()

        # Update workspace folders
        workspace_uri = pathlib.Path(repository_absolute_path).as_uri()
        workspace_name = os.path.basename(repository_absolute_path)

        init_params_config.set_initialization_option(
            [workspace_uri], "workspaceFolders"
        )
        init_params_config.workspace_folders = [
            {
                "uri": workspace_uri,
                "name": workspace_name,
            }
        ]

        # Update bundles with actual intellicode jar path
        init_params_config.set_initialization_option(
            [self.runtime_dependency_paths.intellicode_jar_path], "bundles"
        )

        # Update runtime configuration
        init_params_config.set_initialization_option(
            [
                {
                    "name": "JavaSE-17",
                    "path": self.runtime_dependency_paths.jre_home_path,
                    "default": True,
                }
            ],
            "settings",
            "java",
            "configuration",
            "runtimes",
        )

        # Verify all runtime paths exist
        runtimes = init_params_config.get_initialization_option(
            "settings", "java", "configuration", "runtimes"
        )
        if runtimes:
            for runtime in runtimes:
                assert "name" in runtime, "Runtime missing 'name' field"
                assert "path" in runtime, "Runtime missing 'path' field"
                assert os.path.exists(runtime["path"]), (
                    f"Runtime required for eclipse_jdtls at path {runtime['path']} does not exist"
                )

        # Update gradle configuration
        init_params_config.set_initialization_option(
            self.runtime_dependency_paths.gradle_path,
            "settings",
            "java",
            "import",
            "gradle",
            "home",
        )
        init_params_config.set_initialization_option(
            self.runtime_dependency_paths.jre_path,
            "settings",
            "java",
            "import",
            "gradle",
            "java",
            "home",
        )

        # Convert to dict for LSP communication
        return init_params_config.to_lsp_dict()

    def _get_nested_value(
        self, d: Dict[str, Any], keys: List[str], default: Any = None
    ) -> Any:
        """
        Get a nested value from a dictionary using a path of keys.

        Args:
            d: Dictionary to search
            keys: List of keys representing the path
            default: Default value if path doesn't exist

        Returns:
            Value at the specified path or default
        """
        current = d
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def _set_nested_value(self, d: Dict[str, Any], keys: List[str], value: Any) -> None:
        """
        Set a nested value in a dictionary using a path of keys.

        Creates intermediate dictionaries as needed.

        Args:
            d: Dictionary to modify
            keys: List of keys representing the path
            value: Value to set
        """
        current = d
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        if keys:
            current[keys[-1]] = value

    def _apply_version_overrides(self, initialize_params: InitializeParams) -> None:
        """
        Apply version overrides from MultilspyConfig to the initialize parameters.

        Updates the initialize parameters with overridden JDK, Gradle, and Lombok versions
        if they were specified in the configuration and downloaded/resolved during setup.

        Args:
            initialize_params: The initialize parameters dictionary to modify in-place
        """
        # Override Java version if specified
        if self.config.java_version:
            runtimes = self._get_nested_value(
                initialize_params,
                [
                    "initializationOptions",
                    "settings",
                    "java",
                    "configuration",
                    "runtimes",
                ],
            )
            if runtimes:
                runtime = runtimes[0]
                # Update the runtime name (e.g., "JavaSE-17" -> "JavaSE-21")
                runtime["name"] = f"JavaSE-{self.config.java_version}"
                # Path should already be updated by setupRuntimeDependencies
                runtime["path"] = self.runtime_dependency_paths.jre_home_path
                self.logger.log(
                    f"Applied java_version override: {self.config.java_version} at {runtime['path']}",
                    logging.INFO,
                )

        # Override Gradle version if specified
        if self.config.gradle_version:
            self._set_nested_value(
                initialize_params,
                [
                    "initializationOptions",
                    "settings",
                    "java",
                    "import",
                    "gradle",
                    "home",
                ],
                self.runtime_dependency_paths.gradle_path,
            )
            self._set_nested_value(
                initialize_params,
                [
                    "initializationOptions",
                    "settings",
                    "java",
                    "import",
                    "gradle",
                    "java",
                    "home",
                ],
                self.runtime_dependency_paths.jre_path,
            )
            self.logger.log(
                f"Applied gradle_version override: {self.config.gradle_version} at {self.runtime_dependency_paths.gradle_path}",
                logging.INFO,
            )

        # Override Lombok version if specified
        if self.config.lombok_version:
            self.logger.log(
                f"Applied lombok_version override: {self.config.lombok_version}. "
                f"Using lombok jar at {self.runtime_dependency_paths.lombok_jar_path}",
                logging.INFO,
            )

    @asynccontextmanager
    async def start_server(self) -> AsyncIterator["EclipseJDTLS"]:
        """
        Starts the Eclipse JDTLS Language Server, waits for the server to be ready and yields the LanguageServer instance.

        Usage:
        ```
        async with lsp.start_server():
            # LanguageServer has been initialized and ready to serve requests
            await lsp.request_definition(...)
            await lsp.request_references(...)
            # Shutdown the LanguageServer on exit from scope
        # LanguageServer has been shutdown
        ```
        """

        async def register_capability_handler(params):
            assert "registrations" in params
            for registration in params["registrations"]:
                if registration["method"] == "textDocument/completion":
                    assert registration["registerOptions"]["resolveProvider"] == True
                    assert registration["registerOptions"]["triggerCharacters"] == [
                        ".",
                        "@",
                        "#",
                        "*",
                        " ",
                    ]
                    self.completions_available.set()
                if registration["method"] == "workspace/executeCommand":
                    if (
                        "java.intellicode.enable"
                        in registration["registerOptions"]["commands"]
                    ):
                        self.intellicode_enable_command_available.set()
            return

        async def lang_status_handler(params):
            # TODO: Should we wait for
            # server -> client: {'jsonrpc': '2.0', 'method': 'language/status', 'params': {'type': 'ProjectStatus', 'message': 'OK'}}
            # Before proceeding?
            if params["type"] == "ServiceReady" and params["message"] == "ServiceReady":
                self.service_ready_event.set()

        async def execute_client_command_handler(params):
            assert params["command"] == "_java.reloadBundles.command"
            assert params["arguments"] == []
            return []

        async def window_log_message(msg):
            self.logger.log(f"LSP: window/logMessage: {msg}", logging.INFO)

        async def do_nothing(params):
            return

        self.server.on_request("client/registerCapability", register_capability_handler)
        self.server.on_notification("language/status", lang_status_handler)
        self.server.on_notification("window/logMessage", window_log_message)
        self.server.on_request(
            "workspace/executeClientCommand", execute_client_command_handler
        )
        self.server.on_notification("$/progress", do_nothing)
        self.server.on_notification("textDocument/publishDiagnostics", do_nothing)
        self.server.on_notification("language/actionableNotification", do_nothing)

        async with super().start_server():
            self.logger.log("Starting EclipseJDTLS server process", logging.INFO)
            await self.server.start()
            initialize_params = self._get_initialize_params(self.repository_root_path)

            self.logger.log(
                "Sending initialize request from LSP client to LSP server and awaiting response",
                logging.INFO,
            )
            # Apply version overrides from config if specified
            self._apply_version_overrides(initialize_params)
            init_response = await self.server.send.initialize(initialize_params)
            assert init_response["capabilities"]["textDocumentSync"]["change"] == 2
            assert "completionProvider" not in init_response["capabilities"]
            assert "executeCommandProvider" not in init_response["capabilities"]

            self.server.notify.initialized({})

            self.server.notify.workspace_did_change_configuration(
                {"settings": initialize_params["initializationOptions"]["settings"]}
            )

            await self.intellicode_enable_command_available.wait()

            java_intellisense_members_path = (
                self.runtime_dependency_paths.intellisense_members_path
            )
            assert os.path.exists(java_intellisense_members_path)
            intellicode_enable_result = await self.server.send.execute_command(
                {
                    "command": "java.intellicode.enable",
                    "arguments": [True, java_intellisense_members_path],
                }
            )
            assert intellicode_enable_result

            # TODO: Add comments about why we wait here, and how this can be optimized
            await self.service_ready_event.wait()

            yield self

            await self.server.shutdown()
            await self.server.stop()

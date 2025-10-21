"""
Dependency configuration manager.

Handles applying configuration overrides to runtime dependencies and
marking which dependencies should be downloaded.
"""

import json
import pathlib
from typing import Dict, Any, List, Optional, Set

from multilspy.runtime_dependency_models import RuntimeDependenciesConfig, Dependency
from multilspy.multilspy_config import MultilspyConfig

class DownloadStatus:
    """Enumeration of download statuses."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class DownloadPlan:
    """
    A plan to download a specific dependency.

    Captures all information needed to download and extract a dependency.
    """

    def __init__(
            self,
            dependency_key: str,
            dependency: Dependency,
            url: str,
            archive_type: str,
            destination_path: str,
            status: str = DownloadStatus.PENDING,
    ):
        """
        Initialize a download plan.

        Args:
            dependency_key: Unique key for the dependency
            dependency: The Dependency object
            url: URL to download from
            archive_type: Type of archive (zip, tar.gz, etc.)
            destination_path: Where to extract/install the dependency
            status: Current download status
        """
        self.dependency_key = dependency_key
        self.dependency = dependency
        self.url = url
        self.archive_type = archive_type
        self.destination_path = destination_path
        self.status = status
        self.error_message: Optional[str] = None

    def __repr__(self) -> str:
        return (
            f"DownloadPlan(key={self.dependency_key}, "
            f"status={self.status}, url={self.url})"
        )


class DependencyState:
    """
    Current state of a dependency.

    Tracks whether a dependency has been downloaded and where it's located.
    """

    def __init__(
            self,
            dependency_key: str,
            download_status: str,
            downloaded_path: Optional[str] = None,
            error_message: Optional[str] = None,
    ):
        """
        Initialize dependency state.

        Args:
            dependency_key: Unique key for the dependency
            download_status: Current download status
            downloaded_path: Path where dependency was downloaded/extracted
            error_message: Error message if download failed
        """
        self.dependency_key = dependency_key
        self.download_status = download_status
        self.downloaded_path = downloaded_path
        self.error_message = error_message

    def is_downloaded(self) -> bool:
        """Check if the dependency has been successfully downloaded."""
        return self.download_status == DownloadStatus.COMPLETED

    def __repr__(self) -> str:
        return (
            f"DependencyState(key={self.dependency_key}, "
            f"status={self.download_status}, path={self.downloaded_path})"
        )

class DependencyConfigManager:
    """
    Manages runtime dependency configuration and download decisions.

    Applies configuration overrides from MultilspyConfig to runtime dependencies
    and marks which dependencies need to be downloaded based on configuration.
    """

    def __init__(
        self,
        runtime_deps_config: RuntimeDependenciesConfig,
        multilspy_config: MultilspyConfig,
        base_download_path: str,
    ):
        """
        Initialize the dependency config manager.

        Args:
            runtime_deps_config: Loaded runtime dependencies configuration
            multilspy_config: Multilspy configuration with version overrides
            base_download_path: Base directory for downloading dependencies
        """
        self.runtime_deps = runtime_deps_config
        self.multilspy_config = multilspy_config
        self.base_download_path = base_download_path
        self.download_plans: Dict[str, List[DownloadPlan]] = {}
        self.dependency_states: Dict[str, DependencyState] = {}

    def create_download_plan(self) -> None:
        """
        Create download plans based on configuration and dependencies.

        Analyzes all dependencies and creates download plans for those
        that need to be downloaded based on the current configuration.
        """
        self.download_plans = {}
        all_deps = self.runtime_deps.get_dependencies()

        for dep_key, dep_list in all_deps.items():
            plans = []
            for dep in dep_list:
                plan = self._create_plan_for_dependency(dep_key, dep)
                if plan:
                    plans.append(plan)

            if plans:
                self.download_plans[dep_key] = plans


    def get_dependency(self, key) -> Dict[str, DependencyState]:
        return {
            k:v for k,v in self.dependency_states.items() if k in key
        }



    def _create_plan_for_dependency(
        self, dep_key: str, dep: Dependency
    ) -> Optional["DownloadPlan"]:
        """
        Create a download plan for a specific dependency.

        Args:
            dep_key: The dependency key (e.g., "jdk_versions.17.linux-x64")
            dep: The Dependency object

        Returns:
            DownloadPlan if the dependency should be downloaded, None otherwise
        """
        if not dep.url or not dep.archive_type:
            return None

        # Determine if this dependency should be downloaded based on config
        should_download = self._should_download_dependency(dep_key, dep)

        if not should_download:
            return None

        # Determine download destination
        dest_path = self._get_destination_path(dep_key, dep)

        return DownloadPlan(
            dependency_key=dep_key,
            dependency=dep,
            url=dep.url,
            archive_type=dep.archive_type,
            destination_path=dest_path,
            status=DownloadStatus.PENDING,
        )

    def _should_download_dependency(self, dep_key: str, dep: Dependency) -> bool:
        """
        Determine if a dependency should be downloaded based on configuration.

        Args:
            dep_key: The dependency key
            dep: The dependency object

        Returns:
            True if the dependency should be downloaded
        """
        # Check if specific versions are configured
        if "jdk_versions" in dep_key and self.multilspy_config.java_version:
            return True

        if "gradle_versions" in dep_key and self.multilspy_config.gradle_version:
            return True

        # Always download vscode-java and intellicode for java language server
        if "vscode-java" in dep_key or "intellicode" in dep_key:
            return True

        # Always download gradle
        if "gradle" in dep_key and "gradle_versions" not in dep_key:
            return True

        return False

    def _get_destination_path(self, dep_key: str, dep: Dependency) -> str:
        """
        Determine the destination path for a dependency.

        Args:
            dep_key: The dependency key
            dep: The dependency object

        Returns:
            Absolute path where the dependency should be downloaded
        """
        # Check for explicit install_path in metadata
        if hasattr(dep, "install_path") and dep.install_path:
            return pathlib.Path(self.base_download_path) / dep.install_path

        # Check for relative_extraction_path in metadata
        if hasattr(dep, "relative_extraction_path") and dep.relative_extraction_path:
            return pathlib.Path(self.base_download_path) / dep.relative_extraction_path

        # Derive path from dependency key
        # e.g., "jdk_versions.17.linux-x64" -> "jdk-17-linux-x64"
        parts = dep_key.split(".")
        dir_name = "-".join(parts[:-1]) if len(parts) > 1 else dep_key

        return str(pathlib.Path(self.base_download_path) / dir_name)

    def get_download_plans(self) -> Dict[str, List["DownloadPlan"]]:
        """
        Get all download plans.

        Returns:
            Dictionary mapping dependency keys to download plans
        """
        return self.download_plans

    def get_pending_downloads(self) -> List["DownloadPlan"]:
        """
        Get all pending downloads.

        Returns:
            List of DownloadPlan objects with PENDING status
        """
        pending = []
        for plans in self.download_plans.values():
            pending.extend(p for p in plans if p.status == DownloadStatus.PENDING)
        return pending

    def mark_download_completed(
        self, plan: "DownloadPlan", success: bool = True
    ) -> None:
        """
        Mark a download plan as completed or failed.

        Args:
            plan: The download plan to mark
            success: Whether the download was successful
        """
        plan.status = DownloadStatus.COMPLETED if success else DownloadStatus.FAILED

        # Update dependency state
        state = DependencyState(
            dependency_key=plan.dependency_key,
            download_status=plan.status,
            downloaded_path=plan.destination_path if success else None,
            error_message=None if success else "Download failed",
        )
        self.dependency_states[plan.dependency_key] = state

    def get_dependency_states(self) -> Dict[str, "DependencyState"]:
        """
        Get the states of all dependencies.

        Returns:
            Dictionary mapping dependency keys to DependencyState objects
        """
        return self.dependency_states

    def get_dependency_state(self, dep_key: str) -> Optional["DependencyState"]:
        """
        Get the state of a specific dependency.

        Args:
            dep_key: The dependency key

        Returns:
            DependencyState or None if not found
        """
        return self.dependency_states.get(dep_key)



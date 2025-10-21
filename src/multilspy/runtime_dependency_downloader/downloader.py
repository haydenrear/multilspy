"""
Dependency downloader implementation.

Handles downloading and extracting runtime dependencies.
"""

import logging
import os
import pathlib
from typing import List, Optional

from multilspy.multilspy_logger import MultilspyLogger
from multilspy.multilspy_utils import FileUtils
from multilspy.runtime_dependency_config.config_manager import (
    DownloadPlan,
    DownloadStatus,
    DependencyConfigManager,
)


class DependencyDownloader:
    """
    Downloads and extracts runtime dependencies.

    Executes download plans, manages progress, and updates dependency states.
    """

    def __init__(
        self,
        config_manager: DependencyConfigManager,
        logger: MultilspyLogger,
    ):
        """
        Initialize the dependency downloader.

        Args:
            config_manager: The DependencyConfigManager with download plans
            logger: Logger for progress and error messages
        """
        self.config_manager = config_manager
        self.logger = logger

    def download_all_pending(self) -> bool:
        """
        Download all pending dependencies.

        Returns:
            True if all downloads succeeded, False if any failed
        """
        pending = self.config_manager.get_pending_downloads()

        if not pending:
            self.logger.log(
                "No pending downloads",
                logging.INFO,
            )
            return True

        self.logger.log(
            f"Starting download of {len(pending)} dependencies",
            logging.INFO,
        )

        all_succeeded = True
        for plan in pending:
            success = self.download_dependency(plan)
            if not success:
                all_succeeded = False

        return all_succeeded

    def download_dependency(self, plan: DownloadPlan) -> bool:
        """
        Download a single dependency.

        Args:
            plan: The download plan to execute

        Returns:
            True if download succeeded, False otherwise
        """
        try:
            self.logger.log(
                f"Downloading {plan.dependency_key} from {plan.url}",
                logging.INFO,
            )

            # Update status to in-progress
            plan.status = DownloadStatus.IN_PROGRESS

            # Ensure destination directory exists
            dest_dir = pathlib.Path(plan.destination_path).parent
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Download and extract
            FileUtils.download_and_extract_archive(
                self.logger,
                plan.url,
                str(plan.destination_path),
                plan.archive_type,
            )

            # Verify download
            if not self._verify_download(plan):
                raise RuntimeError(
                    f"Download verification failed for {plan.dependency_key}"
                )

            # Mark as completed
            self.config_manager.mark_download_completed(plan, success=True)

            self.logger.log(
                f"Successfully downloaded {plan.dependency_key} to {plan.destination_path}",
                logging.INFO,
            )

            return True

        except Exception as e:
            error_msg = f"Failed to download {plan.dependency_key}: {str(e)}"
            self.logger.log(error_msg, logging.ERROR)
            plan.error_message = error_msg
            self.config_manager.mark_download_completed(plan, success=False)
            return False

    def _verify_download(self, plan: DownloadPlan) -> bool:
        """
        Verify that a download was successful.

        Args:
            plan: The download plan to verify

        Returns:
            True if verification passed, False otherwise
        """
        dest_path = pathlib.Path(plan.destination_path)

        # Check if destination exists
        if not dest_path.exists():
            self.logger.log(
                f"Destination path does not exist: {dest_path}",
                logging.WARNING,
            )
            return False

        # Check if it's a directory (for extracted archives)
        if dest_path.is_dir():
            # Check if directory is not empty
            if not any(dest_path.iterdir()):
                self.logger.log(
                    f"Destination directory is empty: {dest_path}",
                    logging.WARNING,
                )
                return False
        else:
            # For single files, just check they exist and have content
            if dest_path.stat().st_size == 0:
                self.logger.log(
                    f"Downloaded file is empty: {dest_path}",
                    logging.WARNING,
                )
                return False

        return True

    def get_downloaded_dependencies(self) -> dict:
        """
        Get information about all downloaded dependencies.

        Returns:
            Dictionary mapping dependency keys to their states
        """
        states = self.config_manager.get_dependency_states()
        downloaded = {
            key: state for key, state in states.items() if state.is_downloaded()
        }
        return downloaded

    def get_failed_dependencies(self) -> dict:
        """
        Get information about all failed downloads.

        Returns:
            Dictionary mapping dependency keys to their states
        """
        states = self.config_manager.get_dependency_states()
        failed = {
            key: state
            for key, state in states.items()
            if state.download_status == DownloadStatus.FAILED
        }
        return failed

    def get_download_summary(self) -> dict:
        """
        Get a summary of download results.

        Returns:
            Dictionary with counts of successful, failed, and pending downloads
        """
        states = self.config_manager.get_dependency_states()
        pending = self.config_manager.get_pending_downloads()

        completed = sum(1 for state in states.values() if state.is_downloaded())
        failed = sum(
            1
            for state in states.values()
            if state.download_status == DownloadStatus.FAILED
        )

        return {
            "completed": completed,
            "failed": failed,
            "pending": len(pending),
            "total": completed + failed + len(pending),
        }

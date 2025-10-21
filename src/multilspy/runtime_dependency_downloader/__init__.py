"""
Runtime dependency downloader.

This package handles:
1. Downloading dependencies from URLs
2. Extracting archives
3. Verifying downloads
4. Updating dependency states
"""

from .downloader import DependencyDownloader

__all__ = ["DependencyDownloader"]

"""
Runtime dependency configuration management.

This package handles:
1. Loading and parsing runtime dependencies from JSON
2. Applying configuration overrides based on MultilspyConfig
3. Marking which dependencies should be downloaded and where
4. Coordinating with the download manager for actual downloads
"""

from .config_manager import DependencyConfigManager

__all__ = ["DependencyConfigManager"]

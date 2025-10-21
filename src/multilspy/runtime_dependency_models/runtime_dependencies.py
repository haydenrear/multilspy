"""
Pydantic data models for runtime_dependencies.json across all language servers.

This module provides a comprehensive hierarchical model that captures the
structure of runtime dependencies with flexible versioning, architecture support,
and download configuration.
"""
import typing
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
"""Pydanticdatamodelsforruntime_dependencies.jsonacrossalllanguageservers.
This module provides a comprehensive hierarchical model that captures the
structure of runtime dependencies with flexible versioning, architecture support,
and download configuration.
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field


class Dependency(BaseModel):
    """
    A downloadable dependency at the leaf level.

    Contains the URL, archive optionallytype, withand any additional metadata
    Thisistheactual downloadable resource.
    """

    url: str = Field(..., description="URL to download from")
    archive_type: str = Field(
        ..., alias="archiveType", description="Archive type: zip, tar.gz, tar, gz, etc.")
    description: typing.Optional[str] = Field(alias="_description", description="Description", strict=False, default=None)

    class Config:
        extra = "allow"
        allow_population_by_field_name = True


class RuntimeDependency(BaseModel):
    """
    A runtime dependency that can be:
    1. A single dependency: {url, archiveType, ...}
    2. A map of architectures: {arch1: {url, archiveType}, arch2: {...}}
    3. A map of versions: {version1: RuntimeDependency, version2: {...}}

    Uses flexible schema to support all three patterns.
    """

    url: Optional[str] = Field(None, description="URL (if leaf node)")
    archive_type: Optional[str] = Field(
        None, alias="archiveType", description="Archive type (if leaf node)"
    )

    class Config:
        extra = "allow"
        allow_population_by_field_name = True

    def is_leaf(self) -> bool:
        """Check if this is a leaf node (has url and archiveType)."""
        return self.url is not None and self.archive_type is not None

    def get_child(self, key: str) -> Optional["RuntimeDependency"]:
        """
        Get a child node by key (version, architecture, etc).

        Args:
            key: The child key (e.g., "17", "linux-x64")

        Returns:
            RuntimeDependency or None if not found
        """
        child_data = self.__dict__.get(key)
        if child_data and isinstance(child_data, dict):
            return RuntimeDependency(**child_data)

    def get_all_children(self) -> typing.Union[Dict[str, Dict[str, Any]], "RuntimeDependency"]:
        """
        Get all child nodes.

        Returns:
            Dictionary mapping keys to RuntimeDependency objects
        """
        children = {}
        for key, value in self.__dict__.items():
            if key not in ("url", "archive_type"):
                if isinstance(value, dict):
                    children[key] = RuntimeDependency(value)
        return children

RecursiveDependency = Dict[str, Union[Dependency, str, Dict[str, Union[Dependency, str, Dict[str, Dependency]]]]]
DependencyOrSt = Union[Dependency, str, RecursiveDependency]
DependencyItem = Union[Dependency, str, DependencyOrSt]
DependencyEntryKey = str
DependencyEntry = Union[DependencyItem, Dict[DependencyEntryKey, DependencyItem], Dict[DependencyEntryKey, Dict[DependencyEntryKey, DependencyItem]]]

class RuntimeDependenciesConfig(BaseModel):
    """
    CompleteRuntimeDependenciesConfig(BaseModel):
    Complete runtimeruntime dependenciesdependencies configuration.configuration.

    This is the top-level model that represents the structure of
    runtime_dependencies.json files across all language servers.

    Structure:
    {
      "_description": "...",
      "dependency_name_1": {
        "_description": "...",
        "version_or_arch_1": RuntimeDependency,
        "version_or_arch_2": RuntimeDependency,
        ...
      },
      "dependency_name_2": RuntimeDependency,
      ...
    }

    Each named dependency can be:
    - A single dependency (has url + archiveType)
    - Versioned dependencies (versions map to RuntimeDependency)
    - Architecture-specific (architectures map to RuntimeDependency)
    """

    description: Optional[str] = Field(None, alias="_description")
    dependencies: DependencyEntry = Field(None, alias="dependencies")
    set_deps: Optional[Dict[str, List[Dependency]]] = None

    class Config:
        extra = "allow"
        allow_population_by_field_name = True

    def get_dependencies(self):
        if not self.set_deps and isinstance(self.dependencies, dict):
            self.set_deps = {}
            self.set_deps = self.initialize_dep(self.dependencies)
            if not self.set_deps:
                self.set_deps = {}
        elif not isinstance(self.dependencies, dict):
            self.set_deps = {}

        return self.set_deps

    def initialize_dep(self, d) -> Dict[str, List[Dependency]]:
        if isinstance(d, Dependency):
            return {'': [d]}
        elif isinstance(d, dict):
            if not any([isinstance(n, dict) for n in d.values()]):
                return {'': [Dependency(**d)]}
            else:
                out = {}
                for k, v in d.items():
                    if isinstance(v, dict):
                        initialized = self.initialize_dep(v)
                        for dep_key, dep_value in initialized.items():
                            if dep_key != '':
                                if dep_key in out.keys():
                                    out[k + '.' + dep_key].extend(dep_value)
                                else:
                                    out[k + '.' + dep_key] = dep_value
                            else:
                                if k in out.keys():
                                    out[k].extend(dep_value)
                                else:
                                    out[k] = dep_value

                return out

    def get_dependency(self, d) -> Dict[str, List[Dependency]]:
        if not self.set_deps:
            self.get_dependencies()
        elif len(self.set_deps) == 0:
            return {}

        out = {}
        for dep_key in self.set_deps.keys():
            if dep_key == d:
                return {d: self.set_deps[dep_key]}
            if d in dep_key:
                out[dep_key] = self.set_deps[dep_key]

        return out



"""Repository enrollment and filesystem trust boundaries."""

from .path_policy import RepositoryBoundary, RepositoryPathError

__all__ = ["RepositoryBoundary", "RepositoryPathError"]

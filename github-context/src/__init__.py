"""
GitHub Context Extraction Workflow

A comprehensive workflow for extracting GitHub discussions, PRs, and issues
to provide better context for LLM agents working on software projects.
"""

__version__ = "1.0.0"
__author__ = "django-components team"

from .github_client import GitHubClient
from .models import (
    Comment,
    ContentCollection,
    ContentType,
    Discussion,
    GitHubContent,
    Issue,
    Label,
    PullRequest,
    ReviewStatus,
    User,
)
from .orchestrator import GitHubContextExtractor
from .processor import ContentProcessor
from .storage import StorageManager

__all__ = [
    "GitHubContextExtractor",
    "ContentCollection",
    "GitHubContent",
    "PullRequest",
    "Issue",
    "Discussion",
    "User",
    "Label",
    "Comment",
    "ContentType",
    "ReviewStatus",
    "ContentProcessor",
    "StorageManager",
    "GitHubClient",
]

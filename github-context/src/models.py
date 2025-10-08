"""
Data models for GitHub content extraction.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ContentType(str, Enum):
    """Types of GitHub content."""

    PULL_REQUEST = "pull_request"
    ISSUE = "issue"
    DISCUSSION = "discussion"
    COMMENT = "comment"


class ReviewStatus(str, Enum):
    """Review status for content items."""

    # TODO - WHAT'S DIFFERENCE BETWEEN PENDING AND REVIEW?
    # TODO - WHAT'S DIFFERENCE BETWEEN PENDING AND REVIEW?
    # TODO - WHAT'S DIFFERENCE BETWEEN PENDING AND REVIEW?
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVIEW = "review"


class User(BaseModel):
    """GitHub user information."""

    # TODO - WHAT DO `login`, `site_admin`, `type` MEAN?
    # TODO - WHAT DO `login`, `site_admin`, `type` MEAN?
    # TODO - WHAT DO `login`, `site_admin`, `type` MEAN?
    login: str
    id: int
    type: str = "User"
    site_admin: bool = False


class Label(BaseModel):
    """GitHub label information."""

    name: str
    description: Optional[str] = None


class Comment(BaseModel):
    """GitHub comment information."""

    id: int
    user: Optional[User] = None
    body: str
    created_at: datetime
    updated_at: datetime
    html_url: str
    author_association: str = "NONE"

    @validator("body")
    def validate_body(cls, v):
        """Ensure comment body is not empty."""
        if not v or not v.strip():
            raise ValueError("Comment body cannot be empty")
        return v.strip()


class GitHubContent(BaseModel):
    """Base class for GitHub content items."""

    id: int
    number: int
    title: str
    body: str
    user: Optional[User] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    html_url: str
    repository: str = Field(..., description="Repository in format 'owner/name'")
    content_type: ContentType
    labels: List[Label] = []
    comments: List[Comment] = []
    review_status: ReviewStatus = ReviewStatus.PENDING
    review_notes: Optional[str] = None
    extracted_at: datetime = Field(default_factory=datetime.utcnow)

    @validator("title")
    def sanitize_title(cls, v):
        """Sanitize title for use in filenames."""
        # Remove or replace characters that are problematic in filenames
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", v)
        # Limit length
        return sanitized[:100]

    @validator("repository")
    def validate_repository(cls, v):
        """Validate repository format."""
        if "/" not in v:
            raise ValueError("Repository must be in format 'owner/name'")
        return v

    def get_filename(self) -> str:
        """Generate filename for this content item."""
        owner, name = self.repository.split("/")
        safe_title = re.sub(r'[<>:"/\\|?*]', "_", self.title)
        return f"{owner}_{name}_{self.content_type.value}_{self.number}_{safe_title}"

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata for this content item."""
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "repository": self.repository,
            "content_type": self.content_type.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "html_url": self.html_url,
            "user": self.user.login if self.user else None,
            "labels": [label.name for label in self.labels],
            "comment_count": len(self.comments),
            "review_status": self.review_status.value,
            "review_notes": self.review_notes,
            "extracted_at": self.extracted_at.isoformat(),
        }


class PullRequest(GitHubContent):
    """GitHub pull request information."""

    content_type: ContentType = ContentType.PULL_REQUEST
    draft: bool = False
    merged: bool = False
    mergeable: Optional[bool] = None
    mergeable_state: str = "unknown"
    merged_by: Optional[User] = None
    merged_at: Optional[datetime] = None
    base_branch: str = ""
    head_branch: str = ""
    commits: int = 0
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0


class Issue(GitHubContent):
    """GitHub issue information."""

    content_type: ContentType = ContentType.ISSUE
    state: str = "open"
    locked: bool = False
    assignees: List[User] = []
    milestone: Optional[Dict[str, Any]] = None


class Discussion(GitHubContent):
    """GitHub discussion information."""

    content_type: ContentType = ContentType.DISCUSSION
    category: Optional[Dict[str, Any]] = None
    answer_chosen_at: Optional[datetime] = None
    answer_chosen_by: Optional[User] = None
    is_answered: bool = False


class ContentCollection(BaseModel):
    """Collection of GitHub content items."""

    items: List[GitHubContent] = []
    total_count: int = 0

    def add_item(self, item: GitHubContent):
        """Add an item to the collection."""
        self.items.append(item)
        self.total_count = len(self.items)

    def get_by_status(self, status: ReviewStatus) -> List[GitHubContent]:
        """Get items by review status."""
        return [item for item in self.items if item.review_status == status]

"""
Configuration models for GitHub context extraction workflow.
"""

from datetime import datetime
from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, Field, validator


class GitHubConfig(BaseModel):
    """GitHub API configuration."""

    token: str = Field(..., description="GitHub Personal Access Token")
    rate_limit: int = Field(default=5000, description="API rate limiting (requests per hour)")
    api_url: str = Field(default="https://api.github.com", description="Base URL for GitHub API")


class RepositoryConfig(BaseModel):
    """Repository configuration."""

    owner: str = Field(..., description="Repository owner")
    name: str = Field(..., description="Repository name")
    description: str = Field(default="", description="Repository description")


class TimeRangeConfig(BaseModel):
    """Time range configuration."""

    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(default="now", description="End date (YYYY-MM-DD) or 'now'")
    timezone: str = Field(default="UTC", description="Timezone for date parsing")

    @validator("start_date")
    def validate_start_date(cls, v):
        """Validate start date format."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("start_date must be in YYYY-MM-DD format")
        return v

    @validator("end_date")
    def validate_end_date(cls, v):
        """Validate end date format."""
        if v.lower() != "now":
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("end_date must be in YYYY-MM-DD format or 'now'")
        return v


class ContentTypesConfig(BaseModel):
    """Content types configuration."""

    pull_requests: bool = Field(default=True, description="Extract pull requests")
    issues: bool = Field(default=True, description="Extract issues")
    discussions: bool = Field(default=True, description="Extract discussions")
    comments: bool = Field(default=True, description="Extract comments")
    include_closed: bool = Field(default=True, description="Include closed/merged items")
    include_draft_prs: bool = Field(default=True, description="Include draft PRs")


class ReviewConfig(BaseModel):
    """Review and filtering configuration."""

    default_action: str = Field(default="review", description="Default action for new content")
    auto_approve_authors: List[str] = Field(default=[], description="Auto-approve content from specific authors")
    auto_reject_labels: List[str] = Field(
        default=["spam", "bot"], description="Auto-reject content with specific labels"
    )
    min_comment_length: int = Field(default=10, description="Minimum comment length to include (characters)")

    @validator("default_action")
    def validate_default_action(cls, v):
        """Validate default action."""
        if v not in ["approve", "reject", "review"]:
            raise ValueError("default_action must be one of: approve, reject, review")
        return v


class OutputConfig(BaseModel):
    """Output configuration."""

    data_dir: str = Field(default="data", description="Directory for storing extracted content")
    review_format: str = Field(default="csv", description="File format for review metadata (json/csv)")
    include_raw_responses: bool = Field(default=False, description="Include raw API responses in output")
    compress_files: bool = Field(default=True, description="Compress large files")
    file_pattern: str = Field(
        default="{repo_owner}_{repo_name}_{content_type}_{number}_{title}",
        description="File naming pattern for extracted content",
    )

    @validator("review_format")
    def validate_review_format(cls, v):
        """Validate review format."""
        if v not in ["json", "csv"]:
            raise ValueError("review_format must be one of: json, csv")
        return v


class ProcessingConfig(BaseModel):
    """Processing options configuration."""

    clean_html: bool = Field(default=True, description="Clean HTML from comments")
    strip_markdown: bool = Field(default=False, description="Remove markdown formatting")
    extract_code_blocks: bool = Field(default=True, description="Extract code blocks separately")
    include_metadata: bool = Field(default=True, description="Include metadata in output files")
    max_file_size_mb: int = Field(default=10, description="Maximum file size (MB) before splitting")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Logging level")
    file: str = Field(default="github-context.log", description="Log file path")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format string"
    )

    @validator("level")
    def validate_level(cls, v):
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"level must be one of: {', '.join(valid_levels)}")
        return v.upper()


class AdvancedConfig(BaseModel):
    """Advanced settings configuration."""

    max_retries: int = Field(default=3, description="Retry failed API requests")
    retry_delay: int = Field(default=1, description="Retry delay in seconds")
    batch_size: int = Field(default=100, description="Batch size for API requests")
    cache_duration: int = Field(default=3600, description="Cache API responses (seconds)")
    user_agent: str = Field(
        default="django-components-context-extractor/1.0", description="User agent for API requests"
    )


class ExtractionConfig(BaseModel):
    """Main configuration model for GitHub context extraction."""

    github: GitHubConfig
    repositories: List[RepositoryConfig]
    time_range: TimeRangeConfig
    content_types: ContentTypesConfig
    review: ReviewConfig
    output: OutputConfig
    processing: ProcessingConfig
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    advanced: AdvancedConfig = Field(default_factory=AdvancedConfig)

    @classmethod
    def from_file(cls, config_path: str) -> "ExtractionConfig":
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data)

    def to_file(self, config_path: str) -> None:
        """Save configuration to YAML file."""
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            yaml.dump(self.dict(), f, default_flow_style=False, indent=2)

    def get_date_range(self) -> tuple[datetime, datetime]:
        """Get parsed date range as datetime objects."""
        from datetime import timezone

        # Parse start date
        start_date = datetime.strptime(self.time_range.start_date, "%Y-%m-%d")
        start_date = start_date.replace(tzinfo=timezone.utc)

        # Parse end date
        if self.time_range.end_date.lower() == "now":
            end_date = datetime.now(timezone.utc)
        else:
            end_date = datetime.strptime(self.time_range.end_date, "%Y-%m-%d")
            end_date = end_date.replace(tzinfo=timezone.utc)

        return start_date, end_date

    def validate_github_token(self) -> bool:
        """Validate that GitHub token is set."""
        return bool(self.github.token and self.github.token != "${GITHUB_TOKEN}")

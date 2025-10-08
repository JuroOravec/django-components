"""
GitHub API client for content extraction.
"""

import logging
import os
from datetime import datetime
from typing import List, Optional, Union

from asyncio_throttle import Throttler
from github import Github, GithubException
from github.Issue import Issue as GitHubIssue
from github.IssueComment import IssueComment as GitHubIssueComment
from github.PullRequest import PullRequest as GitHubPullRequest
from github.PullRequestComment import PullRequestComment as GitHubPullRequestComment
from github.Repository import Repository

from .models import Comment, Discussion, Issue, Label, PullRequest, User

logger = logging.getLogger(__name__)


class GitHubClient:
    """GitHub API client with rate limiting and error handling."""

    def __init__(self, token: Optional[str] = None, rate_limit: int = 5000):
        """Initialize GitHub client."""
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token is required. Set GITHUB_TOKEN environment variable.")

        self.github = Github(self.token)
        self.throttler = Throttler(rate_limit=rate_limit, period=3600)  # per hour
        self._test_connection()

    def _test_connection(self):
        """Test GitHub API connection."""
        try:
            user = self.github.get_user()
            logger.info(f"Connected to GitHub as: {user.login}")
        except GithubException as e:
            logger.error(f"Failed to connect to GitHub: {e}")
            raise

    async def get_repository(self, owner: str, name: str) -> Repository:
        """Get GitHub repository."""
        try:
            repo = self.github.get_repo(f"{owner}/{name}")
            logger.info(f"Found repository: {owner}/{name}")
            return repo
        except GithubException as e:
            logger.error(f"Failed to get repository {owner}/{name}: {e}")
            raise

    async def get_pull_requests(
        self,
        repo: Repository,
        start_date: datetime,
        end_date: datetime,
        include_draft: bool = True,
        include_closed: bool = True,
    ) -> List[PullRequest]:
        """Get pull requests within date range."""
        await self.throttler.acquire()

        prs = []
        try:
            # Build query
            query_parts = [f"repo:{repo.full_name}", "is:pr"]

            if not include_draft:
                query_parts.append("is:ready")

            if not include_closed:
                query_parts.append("is:open")

            # Date range
            query_parts.append(f"created:{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}")

            query = " ".join(query_parts)
            logger.info(f"Searching PRs with query: {query}")

            search_results = self.github.search_issues(query=query, sort="created", order="desc")

            for result in search_results:
                try:
                    pr = repo.get_pull(result.number)
                    content_pr = await self._convert_pull_request(pr, repo.full_name)
                    prs.append(content_pr)
                    logger.debug(f"Found PR #{pr.number}: {pr.title}")
                except GithubException as e:
                    logger.warning(f"Failed to get PR #{result.number}: {e}")
                    continue

            logger.info(f"Found {len(prs)} pull requests")
            return prs

        except GithubException as e:
            logger.error(f"Failed to search pull requests: {e}")
            raise

    async def get_issues(
        self,
        repo: Repository,
        start_date: datetime,
        end_date: datetime,
        include_closed: bool = True,
    ) -> List[Issue]:
        """Get issues within date range."""
        await self.throttler.acquire()

        issues = []
        try:
            # Build query
            query_parts = [f"repo:{repo.full_name}", "is:issue"]

            if not include_closed:
                query_parts.append("is:open")

            # Date range
            query_parts.append(f"created:{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}")

            query = " ".join(query_parts)
            logger.info(f"Searching issues with query: {query}")

            search_results = self.github.search_issues(query=query, sort="created", order="desc")

            for result in search_results:
                try:
                    issue = repo.get_issue(result.number)
                    content_issue = await self._convert_issue(issue, repo.full_name)
                    issues.append(content_issue)
                    logger.debug(f"Found issue #{issue.number}: {issue.title}")
                except GithubException as e:
                    logger.warning(f"Failed to get issue #{result.number}: {e}")
                    continue

            logger.info(f"Found {len(issues)} issues")
            return issues

        except GithubException as e:
            logger.error(f"Failed to search issues: {e}")
            raise

    async def get_discussions(self, repo: Repository, start_date: datetime, end_date: datetime) -> List[Discussion]:
        """Get discussions within date range."""
        await self.throttler.acquire()

        discussions = []
        try:
            # Note: GitHub API v3 doesn't support searching discussions directly
            # We'll need to use GraphQL API for this, but for now we'll skip
            # and implement this later if needed
            logger.warning("Discussion search not implemented yet (requires GraphQL API)")
            return discussions

        except GithubException as e:
            logger.error(f"Failed to search discussions: {e}")
            raise

    async def get_comments(self, content_item: Union[GitHubPullRequest, GitHubIssue]) -> List[Comment]:
        """Get comments for a content item (PR, issue, or discussion)."""
        await self.throttler.acquire()

        comments: List[Comment] = []
        try:
            # Get comments based on content type
            if hasattr(content_item, "get_issue_comments"):
                # For PRs and issues
                raw_comments = content_item.get_issue_comments()
            elif hasattr(content_item, "get_review_comments"):
                # For PR review comments
                raw_comments = content_item.get_review_comments()
            else:
                logger.warning(f"Unknown content type for comments: {type(content_item)}")
                return comments

            for raw_comment in raw_comments:
                try:
                    comment = await self._convert_comment(raw_comment)
                    comments.append(comment)
                except Exception as e:
                    logger.warning(f"Failed to convert comment {raw_comment.id}: {e}")
                    continue

            logger.debug(f"Found {len(comments)} comments for {content_item.number}")
            return comments

        except GithubException as e:
            logger.error(f"Failed to get comments: {e}")
            return comments

    async def _convert_pull_request(self, pr: GitHubPullRequest, repo_name: str) -> PullRequest:
        """Convert GitHub PR to our model."""
        # Get comments
        comments = await self.get_comments(pr)

        # Convert labels
        labels = [Label(name=label.name, description=label.description) for label in pr.labels]

        # Convert user
        user = (
            User(
                login=pr.user.login,
                id=pr.user.id,
                type=pr.user.type,
                site_admin=pr.user.site_admin,
            )
            if pr.user
            else None
        )

        # Convert merged by user
        merged_by = None
        if pr.merged_by:
            merged_by = User(
                login=pr.merged_by.login,
                id=pr.merged_by.id,
                type=pr.merged_by.type,
                site_admin=pr.merged_by.site_admin,
            )

        return PullRequest(
            id=pr.id,
            number=pr.number,
            title=pr.title,
            body=pr.body or "",
            user=user,
            created_at=pr.created_at,
            updated_at=pr.updated_at,
            closed_at=pr.closed_at,
            html_url=pr.html_url,
            repository=repo_name,
            labels=labels,
            comments=comments,
            draft=pr.draft,
            merged=pr.merged,
            mergeable=pr.mergeable,
            mergeable_state=pr.mergeable_state,
            merged_by=merged_by,
            merged_at=pr.merged_at,
            base_branch=pr.base.ref,
            head_branch=pr.head.ref,
            commits=pr.commits,
            additions=pr.additions,
            deletions=pr.deletions,
            changed_files=pr.changed_files,
        )

    async def _convert_issue(self, issue: GitHubIssue, repo_name: str) -> Issue:
        """Convert GitHub issue to our model."""
        # Get comments
        comments = await self.get_comments(issue)

        # Convert labels
        labels = [Label(name=label.name, description=label.description) for label in issue.labels]

        # Convert user
        user = (
            User(
                login=issue.user.login,
                id=issue.user.id,
                type=issue.user.type,
                site_admin=issue.user.site_admin,
            )
            if issue.user
            else None
        )

        # Convert assignees
        assignees = []
        for assignee in issue.assignees:
            assignees.append(
                User(
                    login=assignee.login,
                    id=assignee.id,
                    type=assignee.type,
                    site_admin=assignee.site_admin,
                )
            )

        return Issue(
            id=issue.id,
            number=issue.number,
            title=issue.title,
            body=issue.body or "",
            user=user,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
            closed_at=issue.closed_at,
            html_url=issue.html_url,
            repository=repo_name,
            labels=labels,
            comments=comments,
            state=issue.state,
            locked=issue.locked,
            assignees=assignees,
            milestone=issue.milestone.raw_data if issue.milestone else None,
        )

    async def _convert_comment(
        self,
        comment: Union[GitHubIssueComment, GitHubPullRequestComment],
    ) -> Comment:
        """Convert GitHub comment to our model."""
        user = (
            User(
                login=comment.user.login,
                id=comment.user.id,
                type=comment.user.type,
                site_admin=comment.user.site_admin,
            )
            if comment.user
            else None
        )

        return Comment(
            id=comment.id,
            user=user,
            body=comment.body,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            html_url=comment.html_url,
            author_association=comment.author_association,
        )

    def close(self):
        """Close GitHub client connection."""
        if hasattr(self.github, "close"):
            self.github.close()

"""
Main orchestrator for GitHub content extraction workflow.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from .config import ExtractionConfig
from .github_client import GitHubClient
from .models import ContentCollection, ContentType, GitHubContent, ReviewStatus, User
from .processor import ContentProcessor
from .storage import StorageManager

logger = logging.getLogger(__name__)


class GitHubContextExtractor:
    """Main orchestrator for GitHub content extraction workflow."""

    def __init__(self, config_path: str = "config/settings.yaml"):
        """Initialize the extractor with configuration."""
        self.config = ExtractionConfig.from_file(config_path)
        self.github_client = GitHubClient(
            token=self.config.github.token,
            rate_limit=self.config.github.rate_limit,
        )
        self.processor = ContentProcessor(
            clean_html=self.config.processing.clean_html,
            strip_markdown=self.config.processing.strip_markdown,
            extract_code_blocks=self.config.processing.extract_code_blocks,
        )
        self.storage = StorageManager(
            data_dir=self.config.output.data_dir, compress_files=self.config.output.compress_files
        )

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging configuration."""
        level = getattr(logging, self.config.logging.level.upper())

        logging.basicConfig(
            level=level,
            format=self.config.logging.format,
            handlers=[
                logging.FileHandler(self.config.logging.file),
                logging.StreamHandler(),
            ],
        )

    async def discover_content(self) -> ContentCollection:
        """Step 1: Discover content from GitHub repositories."""
        logger.info("Starting content discovery...")

        collection = ContentCollection()
        start_date, end_date = self.config.get_date_range()

        for repo_config in self.config.repositories:
            owner = repo_config.owner
            name = repo_config.name

            logger.info(f"Processing repository: {owner}/{name}")

            try:
                repo = await self.github_client.get_repository(owner, name)

                # Get pull requests
                if self.config.content_types.pull_requests:
                    prs = await self.github_client.get_pull_requests(
                        repo,
                        start_date,
                        end_date,
                        include_draft=self.config.content_types.include_draft_prs,
                        include_closed=self.config.content_types.include_closed,
                    )
                    for pr in prs:
                        collection.add_item(pr)

                # Get issues
                if self.config.content_types.issues:
                    issues = await self.github_client.get_issues(
                        repo, start_date, end_date, include_closed=self.config.content_types.include_closed
                    )
                    for issue in issues:
                        collection.add_item(issue)

                # Get discussions (if implemented)
                if self.config.content_types.discussions:
                    discussions = await self.github_client.get_discussions(repo, start_date, end_date)
                    for discussion in discussions:
                        collection.add_item(discussion)

            except Exception as e:
                logger.error(f"Failed to process repository {owner}/{name}: {e}")
                continue

        logger.info(f"Discovery complete. Found {collection.total_count} items.")
        return collection

    async def process_content(self, collection: ContentCollection) -> ContentCollection:
        """Step 2: Process and clean content."""
        logger.info("Processing content...")

        processed_collection = ContentCollection()

        for item in collection.items:
            try:
                # Apply auto-filtering rules
                if self._should_auto_reject(item):
                    item.review_status = ReviewStatus.REJECTED
                    item.review_notes = "Auto-rejected based on configuration rules"
                elif self._should_auto_approve(item):
                    item.review_status = ReviewStatus.APPROVED
                    item.review_notes = "Auto-approved based on configuration rules"
                else:
                    item.review_status = ReviewStatus.REVIEW

                processed_collection.add_item(item)

            except Exception as e:
                logger.error(f"Failed to process item {item.id}: {e}")
                continue

        logger.info(f"Processing complete. {processed_collection.total_count} items processed.")
        return processed_collection

    async def extract_content(self, collection: ContentCollection) -> List[str]:
        """Step 3: Extract approved content to files."""
        logger.info("Extracting content...")

        extracted_files = []
        approved_items = collection.get_by_status(ReviewStatus.APPROVED)

        for item in approved_items:
            try:
                # Save raw content
                filepath = self.storage.save_content(item, "json")
                extracted_files.append(filepath)

                # Process and save processed content
                processed_data = self.processor.process_content(item)
                processed_filepath = self.storage.save_processed_content(item, processed_data)
                extracted_files.append(processed_filepath)

                # Save as text for LLM consumption
                text_filepath = self.storage.save_content(item, "txt")
                extracted_files.append(text_filepath)

                logger.debug(f"Extracted content: {item.title}")

            except Exception as e:
                logger.error(f"Failed to extract item {item.id}: {e}")
                continue

        logger.info(f"Extraction complete. {len(extracted_files)} files created.")
        return extracted_files

    def generate_review_data(self, collection: ContentCollection) -> str:
        """Generate review data for manual review."""
        logger.info("Generating review data...")

        format_type = self.config.output.review_format
        filepath = self.storage.save_review_data(collection, format_type)

        logger.info(f"Review data saved to: {filepath}")
        return filepath

    def load_review_results(self, review_filepath: str) -> ContentCollection:
        """Load review results and update collection."""
        logger.info("Loading review results...")

        collection = self.storage.load_review_data(review_filepath)

        logger.info(f"Loaded review results. {collection.total_count} items.")
        return collection

    def generate_summary(self, collection: ContentCollection) -> str:
        """Generate a summary of all content."""
        logger.info("Generating summary...")

        summary = self.processor.create_summary(collection.items)
        filepath = self.storage.save_summary(summary)

        logger.info(f"Summary saved to: {filepath}")
        return filepath

    def _should_auto_reject(self, item: GitHubContent) -> bool:
        """Check if item should be auto-rejected."""
        # Check labels
        auto_reject_labels = self.config.review.auto_reject_labels
        item_labels = [label.name for label in item.labels]

        for reject_label in auto_reject_labels:
            if reject_label in item_labels:
                return True

        # Check minimum comment length
        min_length = self.config.review.min_comment_length
        if len(item.body) < min_length:
            return True

        return False

    def _should_auto_approve(self, item: GitHubContent) -> bool:
        """Check if item should be auto-approved."""
        # Check authors
        auto_approve_authors = self.config.review.auto_approve_authors
        if item.user and item.user.login in auto_approve_authors:
            return True

        return False

    async def run_full_workflow(self) -> Dict[str, Any]:
        """Run the complete workflow."""
        logger.info("Starting full GitHub context extraction workflow...")

        results: Dict[str, Any] = {"discovery": None, "review_data": None, "extraction": None, "summary": None}

        try:
            # Step 1: Discover content
            collection = await self.discover_content()
            results["discovery"] = collection

            # Step 2: Process content
            processed_collection = await self.process_content(collection)

            # Step 3: Generate review data
            review_filepath = self.generate_review_data(processed_collection)
            results["review_data"] = review_filepath

            # Step 4: Generate summary
            summary_filepath = self.generate_summary(processed_collection)
            results["summary"] = summary_filepath

            logger.info("Full workflow completed successfully.")

        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            raise

        finally:
            # Clean up
            self.github_client.close()

        return results

    async def run_extraction_only(self, review_filepath: str) -> List[str]:
        """Run only the extraction step with reviewed data."""
        logger.info("Running extraction step...")

        try:
            # Load review results
            collection = self.load_review_results(review_filepath)

            # Extract approved content
            extracted_files = await self.extract_content(collection)

            logger.info("Extraction step completed successfully.")
            return extracted_files

        except Exception as e:
            logger.error(f"Extraction step failed: {e}")
            raise

        finally:
            # Clean up
            self.github_client.close()

    def add_custom_content(self, content_data: Dict[str, Any]) -> GitHubContent:
        """Manually add custom content to the collection."""
        # This would need to be implemented based on the content type
        # For now, this is a placeholder
        logger.info("Custom content addition not implemented yet.")

        return GitHubContent(
            id=0,
            number=0,
            title="Custom Content",
            body="",
            user=User(login="custom", id=0),
            labels=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            html_url="",
            repository="custom/custom",
            content_type=ContentType.ISSUE,
        )

    def cleanup_old_data(self, days: int = 30) -> int:
        """Clean up old data files."""
        return self.storage.cleanup_old_files(days)

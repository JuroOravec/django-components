#!/usr/bin/env python3
"""
Weekly update script for GitHub context extraction workflow.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.orchestrator import GitHubContextExtractor


async def run_weekly_update():
    """Run the weekly update workflow."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("weekly_update.log"), logging.StreamHandler()],
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting weekly GitHub context update...")

    try:
        # Initialize extractor
        extractor = GitHubContextExtractor("config/settings.yaml")

        # Update time range to last week
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        # Update configuration
        extractor.config["time_range"]["start_date"] = start_date.strftime("%Y-%m-%d")
        extractor.config["time_range"]["end_date"] = end_date.strftime("%Y-%m-%d")

        logger.info(f"Time range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

        # Run discovery
        collection = await extractor.discover_content()

        if collection.total_count == 0:
            logger.info("No new content found this week.")
            return

        # Process content
        processed_collection = await extractor.process_content(collection)

        # Generate review data
        review_filepath = extractor.generate_review_data(processed_collection)

        # Generate summary
        summary_filepath = extractor.generate_summary(processed_collection)

        logger.info("Weekly update complete!")
        logger.info(f"Found {collection.total_count} new items")
        logger.info(f"Review data: {review_filepath}")
        logger.info(f"Summary: {summary_filepath}")

        # Clean up old files (keep last 4 weeks)
        removed_count = extractor.cleanup_old_data(days=28)
        logger.info(f"Cleaned up {removed_count} old files")

    except Exception as e:
        logger.error(f"Weekly update failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_weekly_update())

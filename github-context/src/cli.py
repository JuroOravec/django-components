"""
Command-line interface for GitHub context extraction workflow.
"""

import asyncio
from pathlib import Path
from typing import Optional

import click

from .config import (
    ContentTypesConfig,
    ExtractionConfig,
    GitHubConfig,
    OutputConfig,
    ProcessingConfig,
    RepositoryConfig,
    ReviewConfig,
    TimeRangeConfig,
)
from .orchestrator import GitHubContextExtractor


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """GitHub Context Extraction Workflow CLI."""
    pass


@cli.command()
@click.option("--config", "-c", default="config/settings.yaml", help="Configuration file path")
@click.option("--output", "-o", help="Output directory for extracted content")
def init(config: str, output: Optional[str]):
    """Initialize the workflow with a new configuration."""
    try:
        # Create default configuration
        default_config = ExtractionConfig(
            github=GitHubConfig(token="${GITHUB_TOKEN}", rate_limit=5000),
            repositories=[
                RepositoryConfig(
                    owner="django-components",
                    name="django-components",
                    description="Main repository",
                )
            ],
            time_range=TimeRangeConfig(start_date="2024-01-01", end_date="now"),
            content_types=ContentTypesConfig(),
            review=ReviewConfig(),
            output=OutputConfig(data_dir=output or "data"),
            processing=ProcessingConfig(),
        )

        # Save configuration
        config_path = Path(config)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        default_config.to_file(config)

        click.echo(f"Configuration initialized at: {config}")
        click.echo("Please update the GitHub token and repository settings.")

    except Exception as e:
        click.echo(f"Failed to initialize configuration: {e}", err=True)


@cli.command()
@click.option("--config", "-c", default="config/settings.yaml", help="Configuration file path")
def discover(config: str):
    """Discover content from GitHub repositories."""

    async def run_discovery():
        try:
            extractor = GitHubContextExtractor(config)
            collection = await extractor.discover_content()

            click.echo(f"Discovered {collection.total_count} items:")
            for item in collection.items:
                click.echo(f"  - {item.content_type.value} #{item.number}: {item.title}")

        except Exception as e:
            click.echo(f"Discovery failed: {e}", err=True)

    asyncio.run(run_discovery())


@cli.command()
@click.option("--config", "-c", default="config/settings.yaml", help="Configuration file path")
@click.option("--output", "-o", help="Output file for review data")
def extract(config: str, output: Optional[str]):
    """Extract content and generate review data."""

    async def run_extraction():
        try:
            extractor = GitHubContextExtractor(config)

            # Run discovery and processing
            collection = await extractor.discover_content()
            processed_collection = await extractor.process_content(collection)

            # Generate review data
            if output:
                # Save to specified output file
                extractor.storage.save_review_data(processed_collection, "csv")
                # Note: The storage manager doesn't support custom output paths yet
                click.echo("Review data saved to default location")
            else:
                # Use default location
                review_filepath = extractor.generate_review_data(processed_collection)
                click.echo(f"Review data saved to: {review_filepath}")

        except Exception as e:
            click.echo(f"Extraction failed: {e}", err=True)

    asyncio.run(run_extraction())


@cli.command()
@click.option("--config", "-c", default="config/settings.yaml", help="Configuration file path")
@click.option("--review-file", "-r", required=True, help="Review data file path")
def run(config: str, review_file: str):
    """Run the complete workflow."""

    async def run_workflow():
        try:
            extractor = GitHubContextExtractor(config)

            # Load review results and extract approved content
            extracted_files = await extractor.run_extraction_only(review_file)

            click.echo(f"Workflow completed. {len(extracted_files)} files extracted.")
            for filepath in extracted_files:
                click.echo(f"  - {filepath}")

        except Exception as e:
            click.echo(f"Workflow failed: {e}", err=True)

    asyncio.run(run_workflow())


@cli.command()
@click.option("--config", "-c", default="config/settings.yaml", help="Configuration file path")
@click.option("--days", "-d", default=30, help="Number of days to keep")
def cleanup(config: str, days: int):
    """Clean up old data files."""
    try:
        extractor = GitHubContextExtractor(config)
        removed_count = extractor.cleanup_old_data(days)
        click.echo(f"Cleaned up {removed_count} old files.")

    except Exception as e:
        click.echo(f"Cleanup failed: {e}", err=True)


@cli.command()
@click.option("--config", "-c", default="config/settings.yaml", help="Configuration file path")
def review(config: str):
    """Open review data for manual review."""
    try:
        extractor = GitHubContextExtractor(config)

        # Find review data file
        data_dir = Path(extractor.config.output.data_dir)
        review_files = list(data_dir.glob("*_review.*"))

        if not review_files:
            click.echo("No review data found. Run 'extract' first.", err=True)
            return

        # Use the most recent review file
        latest_file = max(review_files, key=lambda f: f.stat().st_mtime)

        click.echo(f"Opening review file: {latest_file}")
        click.echo("Please review the data and update the status column.")
        click.echo("Then run 'run' with the updated file.")

        # Try to open the file with default application
        import subprocess
        import sys

        if sys.platform == "darwin":  # macOS
            subprocess.run(["open", str(latest_file)])
        elif sys.platform == "win32":  # Windows
            subprocess.run(["start", str(latest_file)], shell=True)
        else:  # Linux
            subprocess.run(["xdg-open", str(latest_file)])

    except Exception as e:
        click.echo(f"Review failed: {e}", err=True)


@cli.command()
@click.option("--config", "-c", default="config/settings.yaml", help="Configuration file path")
def status(config: str):
    """Show workflow status."""
    try:
        extractor = GitHubContextExtractor(config)

        # Check configuration
        click.echo("Configuration:")
        click.echo(f"  GitHub Token: {'✓ Set' if extractor.config.validate_github_token() else '✗ Not set'}")
        click.echo(f"  Repositories: {len(extractor.config.repositories)}")
        for repo in extractor.config.repositories:
            click.echo(f"    - {repo.owner}/{repo.name}")

        # Check data directory
        data_dir = Path(extractor.config.output.data_dir)
        if data_dir.exists():
            files = list(data_dir.glob("*"))
            click.echo(f"  Data Directory: {data_dir} ({len(files)} files)")
        else:
            click.echo(f"  Data Directory: {data_dir} (not found)")

        # Check for review files
        if data_dir.exists():
            review_files = list(data_dir.glob("*_review.*"))
            if review_files:
                latest_file = max(review_files, key=lambda f: f.stat().st_mtime)
                click.echo(f"  Latest Review: {latest_file}")
            else:
                click.echo("  Latest Review: None")

    except Exception as e:
        click.echo(f"Status check failed: {e}", err=True)


if __name__ == "__main__":
    cli()

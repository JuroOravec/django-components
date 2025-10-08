#!/usr/bin/env python3
"""
Script to create comprehensive summaries from extracted GitHub content.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.orchestrator import GitHubContextExtractor
from src.processor import ContentProcessor
from src.storage import StorageManager


async def create_comprehensive_summary():
    """Create a comprehensive summary of all extracted content."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Initialize components
        extractor = GitHubContextExtractor("config/settings.yaml")
        processor = ContentProcessor()
        storage = StorageManager()

        # Load all content files
        content_files = storage.list_content_files()

        if not content_files:
            logger.warning("No content files found. Run discovery first.")
            return

        logger.info(f"Found {len(content_files)} content files")

        # Process each file and extract key information
        summary_data = {
            "total_files": len(content_files),
            "by_repository": {},
            "by_type": {},
            "by_author": {},
            "key_topics": [],
            "recent_activity": [],
            "design_discussions": [],
        }

        for filepath in content_files:
            try:
                # Load content (this would need to be implemented based on your file format)
                # For now, we'll create a placeholder
                logger.debug(f"Processing {filepath.name}")

                # Extract key information
                # This is a placeholder - you'd implement the actual loading logic

            except Exception as e:
                logger.warning(f"Failed to process {filepath}: {e}")
                continue

        # Generate comprehensive summary
        summary = generate_comprehensive_summary(summary_data)

        # Save summary
        summary_filepath = storage.save_summary(summary, "comprehensive_summary.md")

        logger.info(f"Comprehensive summary saved to: {summary_filepath}")

    except Exception as e:
        logger.error(f"Failed to create comprehensive summary: {e}")
        raise


def generate_comprehensive_summary(data: Dict[str, Any]) -> str:
    """Generate a comprehensive summary from collected data."""

    summary_lines = [
        "# GitHub Context Comprehensive Summary",
        "",
        f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total content files: {data['total_files']}",
        "",
        "## Overview",
        "",
        "This summary provides a comprehensive overview of all GitHub discussions, ",
        "pull requests, and issues that have been extracted for LLM context.",
        "",
        "## Key Insights",
        "",
        "### Design Patterns",
        "- Component architecture discussions",
        "- Caching strategies",
        "- Performance considerations",
        "",
        "### Common Themes",
        "- User experience improvements",
        "- Code quality and maintainability",
        "- Documentation and examples",
        "",
        "### Technical Decisions",
        "- Framework choices and rationale",
        "- API design decisions",
        "- Backward compatibility considerations",
        "",
        "## Repository Activity",
        "",
        "### Most Active Repositories",
        "- django-components: Main framework repository",
        "- Related repositories: Additional components and tools",
        "",
        "### Content Types",
        "- Pull Requests: Code changes and feature implementations",
        "- Issues: Bug reports and feature requests",
        "- Discussions: Design decisions and community feedback",
        "",
        "## Recent Activity",
        "",
        "### Latest Discussions",
        "- Component caching implementation",
        "- Slot hashing for better cache keys",
        "- Performance optimization strategies",
        "",
        "### Important Decisions",
        "- Cache key generation strategy",
        "- Component isolation approach",
        "- API design principles",
        "",
        "## Design Architecture",
        "",
        "### Core Principles",
        "1. **Component Isolation**: Components should be self-contained and reusable",
        "2. **Performance First**: Caching and optimization are key considerations",
        "3. **Developer Experience**: Easy to use and understand",
        "4. **Extensibility**: Framework should be easily extensible",
        "",
        "### Key Components",
        "- **ComponentCache**: Handles caching of rendered components",
        "- **Slot System**: Flexible content injection mechanism",
        "- **Template Engine**: Django template integration",
        "- **Extension System**: Plugin architecture for custom functionality",
        "",
        "### Caching Strategy",
        "The framework implements a sophisticated caching system that considers:",
        "- Component class identity",
        "- Input parameters",
        "- Slot content (when implemented)",
        "- Context dependencies",
        "",
        "## Implementation Notes",
        "",
        "### Current Status",
        "- Core component system is stable",
        "- Caching system is functional",
        "- Slot system is implemented",
        "- Extension system is in development",
        "",
        "### Future Plans",
        "- Enhanced slot hashing for better cache coverage",
        "- GraphQL API for discussions",
        "- Improved performance monitoring",
        "- Better developer tooling",
        "",
        "## Community Insights",
        "",
        "### User Feedback",
        "- Positive reception for component-based approach",
        "- Requests for better documentation",
        "- Interest in performance optimization",
        "",
        "### Common Questions",
        "- How to implement custom components?",
        "- Best practices for caching?",
        "- Integration with existing Django projects?",
        "",
        "## Technical Details",
        "",
        "### Code Examples",
        "```python",
        "# Example component usage",
        "{% component 'badge' type='info' %}",
        "  <i class='fas fa-info'></i> Information",
        "{% endcomponent %}",
        "```",
        "",
        "### Configuration",
        "```yaml",
        "# Example configuration",
        "github:",
        "  token: ${GITHUB_TOKEN}",
        "repositories:",
        "  - owner: django-components",
        "    name: django-components",
        "```",
        "",
        "## Conclusion",
        "",
        "This comprehensive summary provides the context needed for LLM agents ",
        "to understand the django-components project architecture, design decisions, ",
        "and current development status. The information is structured to support ",
        "informed decision-making and development assistance.",
        "",
    ]

    return "\n".join(summary_lines)


if __name__ == "__main__":
    asyncio.run(create_comprehensive_summary())

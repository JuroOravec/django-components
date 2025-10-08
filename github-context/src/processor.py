"""
Content processor for cleaning and formatting GitHub content.
"""

import logging
import re
from typing import Any, Dict, List

import html2text
from bs4 import BeautifulSoup

from .models import Comment, GitHubContent

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Process and clean GitHub content for better LLM consumption."""

    def __init__(self, clean_html: bool = True, strip_markdown: bool = False, extract_code_blocks: bool = True):
        """Initialize content processor."""
        self.clean_html = clean_html
        self.strip_markdown = strip_markdown
        self.extract_code_blocks = extract_code_blocks
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False

    def process_content(self, content: GitHubContent) -> Dict[str, Any]:
        """Process a content item and return cleaned data."""
        processed = {"metadata": content.get_metadata(), "content": self._process_body(content.body), "comments": []}

        # Process comments
        for comment in content.comments:
            processed_comment = self._process_comment(comment)
            processed["comments"].append(processed_comment)

        return processed

    def _process_body(self, body: str) -> Dict[str, Any]:
        """Process the main body content."""
        if not body or not body.strip():
            return {"text": "", "code_blocks": [], "links": []}

        processed = {"text": body, "code_blocks": [], "links": []}

        # Extract code blocks if enabled
        if self.extract_code_blocks:
            processed["code_blocks"] = self._extract_code_blocks(body)

        # Extract links
        processed["links"] = self._extract_links(body)

        # Clean HTML if enabled
        if self.clean_html:
            processed["text"] = self._clean_html(processed["text"])

        # Strip markdown if enabled
        if self.strip_markdown:
            processed["text"] = self._strip_markdown(processed["text"])

        return processed

    def _process_comment(self, comment: Comment) -> Dict[str, Any]:
        """Process a comment."""
        return {
            "id": comment.id,
            "user": comment.user.login if comment.user else "Unknown",
            "created_at": comment.created_at.isoformat(),
            "updated_at": comment.updated_at.isoformat(),
            "author_association": comment.author_association,
            "content": self._process_body(comment.body),
        }

    def _extract_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """Extract code blocks from markdown text."""
        code_blocks = []

        # Match markdown code blocks
        pattern = r"```(\w+)?\n(.*?)```"
        matches = re.finditer(pattern, text, re.DOTALL)

        for match in matches:
            language = match.group(1) or "text"
            code = match.group(2).strip()
            code_blocks.append({"language": language, "code": code})

        # Match inline code
        inline_pattern = r"`([^`]+)`"
        inline_matches = re.finditer(inline_pattern, text)

        for match in inline_matches:
            code = match.group(1)
            code_blocks.append({"language": "inline", "code": code})

        return code_blocks

    def _extract_links(self, text: str) -> List[Dict[str, str]]:
        """Extract links from text."""
        links = []

        # Match markdown links
        pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        matches = re.finditer(pattern, text)

        for match in matches:
            links.append({"text": match.group(1), "url": match.group(2)})

        # Match plain URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        url_matches = re.finditer(url_pattern, text)

        for match in url_matches:
            url = match.group(0)
            links.append({"text": url, "url": url})

        return links

    def _clean_html(self, text: str) -> str:
        """Clean HTML from text."""
        if not text:
            return text

        try:
            # Parse HTML
            soup = BeautifulSoup(text, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Convert to text
            cleaned = self.html_converter.handle(str(soup))

            # Clean up extra whitespace
            cleaned = re.sub(r"\n\s*\n", "\n\n", cleaned)
            cleaned = re.sub(r" +", " ", cleaned)

            return cleaned.strip()

        except Exception as e:
            logger.warning(f"Failed to clean HTML: {e}")
            return text

    def _strip_markdown(self, text: str) -> str:
        """Strip markdown formatting from text."""
        if not text:
            return text

        # Remove headers
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

        # Remove bold and italic
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"__([^_]+)__", r"\1", text)
        text = re.sub(r"_([^_]+)_", r"\1", text)

        # Remove strikethrough
        text = re.sub(r"~~([^~]+)~~", r"\1", text)

        # Remove code blocks (keep content)
        text = re.sub(r"```\w*\n(.*?)```", r"\1", text, flags=re.DOTALL)
        text = re.sub(r"`([^`]+)`", r"\1", text)

        # Remove links (keep text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        # Remove images
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)

        # Remove blockquotes
        text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)

        # Clean up extra whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = re.sub(r" +", " ", text)

        return text.strip()

    def format_for_llm(self, content: GitHubContent) -> str:
        """Format content specifically for LLM consumption."""
        processed = self.process_content(content)

        # Build formatted output
        lines = []

        # Header
        lines.append(f"# {processed['metadata']['title']}")
        lines.append(f"**Repository:** {processed['metadata']['repository']}")
        lines.append(f"**Type:** {processed['metadata']['content_type']}")
        lines.append(f"**Number:** #{processed['metadata']['number']}")
        lines.append(f"**Author:** {processed['metadata']['user'] or 'Unknown'}")
        lines.append(f"**Created:** {processed['metadata']['created_at']}")
        lines.append(f"**URL:** {processed['metadata']['html_url']}")

        if processed["metadata"]["labels"]:
            lines.append(f"**Labels:** {', '.join(processed['metadata']['labels'])}")

        lines.append("")

        # Main content
        lines.append("## Content")
        lines.append(processed["content"]["text"])
        lines.append("")

        # Code blocks
        if processed["content"]["code_blocks"]:
            lines.append("## Code Blocks")
            for i, block in enumerate(processed["content"]["code_blocks"], 1):
                lines.append(f"### Code Block {i} ({block['language']})")
                lines.append("```" + block["language"])
                lines.append(block["code"])
                lines.append("```")
                lines.append("")

        # Links
        if processed["content"]["links"]:
            lines.append("## Links")
            for link in processed["content"]["links"]:
                lines.append(f"- [{link['text']}]({link['url']})")
            lines.append("")

        # Comments
        if processed["comments"]:
            lines.append("## Comments")
            for comment in processed["comments"]:
                lines.append(f"### Comment by {comment['user']} ({comment['created_at']})")
                lines.append(comment["content"]["text"])
                lines.append("")

        return "\n".join(lines)

    def create_summary(self, contents: List[GitHubContent]) -> str:
        """Create a summary of multiple content items."""
        summary_lines = []

        # Group by type
        by_type = {}
        for content in contents:
            content_type = content.content_type.value
            if content_type not in by_type:
                by_type[content_type] = []
            by_type[content_type].append(content)

        # Summary by type
        for content_type, items in by_type.items():
            summary_lines.append(f"## {content_type.replace('_', ' ').title()}s ({len(items)})")

            for item in sorted(items, key=lambda x: x.created_at, reverse=True):
                status = (
                    "🟢"
                    if item.review_status.value == "approved"
                    else "🟡" if item.review_status.value == "review" else "🔴"
                )
                summary_lines.append(
                    f"{status} #{item.number}: {item.title} (by {item.user.login if item.user else 'Unknown'})"
                )

            summary_lines.append("")

        return "\n".join(summary_lines)

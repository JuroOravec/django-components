"""
Storage manager for GitHub content extraction.
"""

import gzip
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .models import ContentCollection, GitHubContent

logger = logging.getLogger(__name__)


class StorageManager:
    """Manage storage of GitHub content and metadata."""

    def __init__(self, data_dir: str = "data", compress_files: bool = True):
        """Initialize storage manager."""
        self.data_dir = Path(data_dir)
        self.compress_files = compress_files

        # Create directory structure
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.metadata_dir = self.data_dir / "metadata"

        for directory in [self.raw_dir, self.processed_dir, self.metadata_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def save_content(self, content: GitHubContent, format_type: str = "json") -> str:
        """Save a content item to file."""
        filename = self._get_content_filename(content, format_type)
        filepath = self.raw_dir / filename

        # Prepare data for saving
        data = content.dict()

        # Save based on format
        if format_type == "json":
            self._save_json(data, filepath)
        elif format_type == "txt":
            self._save_text(content, filepath)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

        logger.info(f"Saved content to: {filepath}")
        return str(filepath)

    def save_collection(self, collection: ContentCollection, format_type: str = "json") -> str:
        """Save a collection of content items."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"collection_{timestamp}.{format_type}"
        filepath = self.metadata_dir / filename

        if format_type == "json":
            self._save_json(collection.dict(), filepath)
        elif format_type == "csv":
            self._save_csv(collection, filepath)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

        logger.info(f"Saved collection to: {filepath}")
        return str(filepath)

    def load_collection(self, filepath: str) -> ContentCollection:
        """Load a collection from file."""
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"Collection file not found: {filepath}")

        if path.suffix == ".json":
            data = self._load_json(path)
        elif path.suffix == ".csv":
            data = self._load_csv(path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        return ContentCollection(**data)

    def save_review_data(self, collection: ContentCollection, format_type: str = "csv") -> str:
        """Save review data in a format suitable for manual review."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"review_data_{timestamp}.{format_type}"
        filepath = self.metadata_dir / filename

        if format_type == "csv":
            self._save_review_csv(collection, filepath)
        elif format_type == "json":
            self._save_review_json(collection, filepath)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

        logger.info(f"Saved review data to: {filepath}")
        return str(filepath)

    def load_review_data(self, filepath: str) -> ContentCollection:
        """Load review data and convert back to collection."""
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"Review file not found: {filepath}")

        if path.suffix == ".csv":
            return self._load_review_csv(path)
        elif path.suffix == ".json":
            return self._load_review_json(path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def save_processed_content(self, content: GitHubContent, processed_data: Dict[str, Any]) -> str:
        """Save processed content data."""
        filename = f"{content.get_filename()}_processed.json"
        filepath = self.processed_dir / filename

        self._save_json(processed_data, filepath)

        logger.info(f"Saved processed content to: {filepath}")
        return str(filepath)

    def save_summary(self, summary: str, filename: Optional[str] = None) -> str:
        """Save a summary document."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_{timestamp}.md"

        filepath = self.data_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(summary)

        logger.info(f"Saved summary to: {filepath}")
        return str(filepath)

    def _get_content_filename(self, content: GitHubContent, format_type: str) -> str:
        """Generate filename for content item."""
        base_filename = content.get_filename()
        return f"{base_filename}.{format_type}"

    def _save_json(self, data: Dict[str, Any], filepath: Path):
        """Save data as JSON."""
        if self.compress_files:
            filepath = filepath.with_suffix(filepath.suffix + ".gz")
            with gzip.open(filepath, "wt", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

    def _save_text(self, content: GitHubContent, filepath: Path):
        """Save content as plain text."""
        text_content = f"""Title: {content.title}
Repository: {content.repository}
Type: {content.content_type.value}
Number: #{content.number}
Author: {content.user.login if content.user else 'Unknown'}
Created: {content.created_at}
URL: {content.html_url}

Labels: {', '.join([label.name for label in content.labels])}

Content:
{content.body}

Comments:
"""

        for comment in content.comments:
            text_content += f"\n--- Comment by {comment.user.login if comment.user else 'Unknown'} ---\n"
            text_content += f"Created: {comment.created_at}\n"
            text_content += f"{comment.body}\n"

        if self.compress_files:
            filepath = filepath.with_suffix(filepath.suffix + ".gz")
            with gzip.open(filepath, "wt", encoding="utf-8") as f:
                f.write(text_content)
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text_content)

    def _save_csv(self, collection: ContentCollection, filepath: Path):
        """Save collection as CSV."""
        rows = []
        for item in collection.items:
            row = {
                "id": item.id,
                "number": item.number,
                "title": item.title,
                "repository": item.repository,
                "content_type": item.content_type.value,
                "user": item.user.login if item.user else None,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
                "closed_at": item.closed_at.isoformat() if item.closed_at else None,
                "html_url": item.html_url,
                "labels": ", ".join([label.name for label in item.labels]),
                "comment_count": len(item.comments),
                "review_status": item.review_status.value,
                "review_notes": item.review_notes,
                "extracted_at": item.extracted_at.isoformat(),
            }
            rows.append(row)

        if rows:
            df = pd.DataFrame(rows)
            df.to_csv(filepath, index=False)

    def _save_review_csv(self, collection: ContentCollection, filepath: Path):
        """Save review data as CSV with review columns."""
        rows = []
        for item in collection.items:
            row = {
                "id": item.id,
                "number": item.number,
                "title": item.title,
                "repository": item.repository,
                "content_type": item.content_type.value,
                "user": item.user.login if item.user else None,
                "created_at": item.created_at.isoformat(),
                "html_url": item.html_url,
                "labels": ", ".join([label.name for label in item.labels]),
                "comment_count": len(item.comments),
                "body_preview": item.body[:200] + "..." if len(item.body) > 200 else item.body,
                "review_status": item.review_status.value,
                "review_notes": item.review_notes or "",
                "action": "review",  # Column for manual review
                "notes": "",  # Column for manual notes
            }
            rows.append(row)

        if rows:
            df = pd.DataFrame(rows)
            df.to_csv(filepath, index=False)

    def _save_review_json(self, collection: ContentCollection, filepath: Path):
        """Save review data as JSON."""
        review_data = {
            "metadata": {
                "total_items": len(collection.items),
                "created_at": datetime.now().isoformat(),
                "format": "review",
            },
            "items": [item.dict() for item in collection.items],
        }

        self._save_json(review_data, filepath)

    def _load_json(self, filepath: Path) -> Dict[str, Any]:
        """Load data from JSON file."""
        if filepath.suffix == ".gz":
            with gzip.open(filepath, "rt", encoding="utf-8") as f:
                return json.load(f)
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)

    def _load_csv(self, filepath: Path) -> Dict[str, Any]:
        """Load data from CSV file."""
        df = pd.read_csv(filepath)
        # Convert DataFrame back to collection format
        # This is a simplified conversion - you might need more complex logic
        items = []
        for _, row in df.iterrows():
            # Create a basic content item from row data
            # This is a placeholder - you'd need to reconstruct the full object
            pass

        return {"items": items, "total_count": len(items)}

    def _load_review_csv(self, filepath: Path) -> ContentCollection:
        """Load review data from CSV and convert to collection."""
        df = pd.read_csv(filepath)

        # This would need to reconstruct the full content objects
        # For now, return an empty collection
        # You'd need to implement the full reconstruction logic
        return ContentCollection()

    def _load_review_json(self, filepath: Path) -> ContentCollection:
        """Load review data from JSON."""
        data = self._load_json(filepath)
        return ContentCollection(**data)

    def list_content_files(self, content_type: Optional[str] = None) -> List[Path]:
        """List all content files in the raw directory."""
        files = list(self.raw_dir.glob("*"))

        if content_type:
            files = [f for f in files if content_type in f.name]

        return sorted(files)

    def get_file_info(self, filepath: Path) -> Dict[str, Any]:
        """Get information about a file."""
        stat = filepath.stat()
        return {
            "name": filepath.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "path": str(filepath),
        }

    def cleanup_old_files(self, days: int = 30) -> int:
        """Clean up files older than specified days."""
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        removed_count = 0

        for directory in [self.raw_dir, self.processed_dir, self.metadata_dir]:
            for filepath in directory.glob("*"):
                if filepath.stat().st_mtime < cutoff:
                    filepath.unlink()
                    removed_count += 1
                    logger.info(f"Removed old file: {filepath}")

        return removed_count

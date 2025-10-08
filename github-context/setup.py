#!/usr/bin/env python3
"""
Setup script for GitHub Context Extraction Workflow.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True


def install_dependencies():
    """Install required dependencies."""
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        return False

    return run_command("pip install -r requirements.txt", "Installing dependencies")


def create_directories():
    """Create necessary directories."""
    directories = ["config", "data/raw", "data/processed", "data/metadata", "scripts"]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"📁 Created directory: {directory}")


def check_github_token():
    """Check if GitHub token is set."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("⚠️  GITHUB_TOKEN environment variable not set")
        print("💡 Please set your GitHub token:")
        print("   export GITHUB_TOKEN='your-github-token'")
        print("   or add it to your shell profile (.bashrc, .zshrc, etc.)")
        return False

    print("✅ GitHub token found")
    return True


def create_sample_config():
    """Create a sample configuration file if it doesn't exist."""
    config_file = Path("config/settings.yaml")
    if config_file.exists():
        print("✅ Configuration file already exists")
        return True

    print("📝 Creating sample configuration file...")

    sample_config = """# GitHub Context Extraction Configuration

# GitHub API Configuration
github:
  # GitHub Personal Access Token (required for API access)
  # Set this as environment variable GITHUB_TOKEN or create a token file
  token: ${GITHUB_TOKEN}

  # API rate limiting (requests per hour)
  rate_limit: 5000

  # Base URL for GitHub API (use GitHub Enterprise URL if needed)
  api_url: "https://api.github.com"

# Repositories to monitor
repositories:
  - owner: "django-components"
    name: "django-components"
    description: "Main django-components repository"
  # Add more repositories as needed
  # - owner: "your-org"
  #   name: "related-repo"
  #   description: "Related repository"

# Time range for content discovery
time_range:
  # Start date (inclusive) - format: YYYY-MM-DD
  start_date: "2024-01-01"

  # End date (inclusive) - format: YYYY-MM-DD or "now" for current date
  end_date: "now"

  # Timezone for date parsing (default: UTC)
  timezone: "UTC"

# Content types to extract
content_types:
  pull_requests: true
  issues: true
  discussions: true
  comments: true

  # Include closed/merged items
  include_closed: true

  # Include draft PRs
  include_draft_prs: true

# Review and filtering
review:
  # Default action for new content (approve/reject/review)
  default_action: "review"

  # Auto-approve content from specific authors
  auto_approve_authors: []

  # Auto-reject content with specific labels
  auto_reject_labels: ["spam", "bot"]

  # Minimum comment length to include (characters)
  min_comment_length: 10

# Output configuration
output:
  # Directory for storing extracted content
  data_dir: "data"

  # File format for review metadata (json/csv)
  review_format: "csv"

  # Include raw API responses in output
  include_raw_responses: false

  # Compress large files
  compress_files: true

  # File naming pattern for extracted content
  # Available placeholders: {repo_owner}, {repo_name}, {content_type}, {number}, {title}
  file_pattern: "{repo_owner}_{repo_name}_{content_type}_{number}_{title}"

# Processing options
processing:
  # Clean HTML from comments
  clean_html: true

  # Remove markdown formatting
  strip_markdown: false

  # Extract code blocks separately
  extract_code_blocks: true

  # Include metadata in output files
  include_metadata: true

  # Maximum file size (MB) before splitting
  max_file_size_mb: 10

# Logging
logging:
  level: "INFO"
  file: "github-context.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Advanced settings
advanced:
  # Retry failed API requests
  max_retries: 3
  retry_delay: 1

  # Batch size for API requests
  batch_size: 100

  # Cache API responses (seconds)
  cache_duration: 3600

  # User agent for API requests
  user_agent: "django-components-context-extractor/1.0"
"""

    with open(config_file, "w") as f:
        f.write(sample_config)

    print("✅ Sample configuration created: config/settings.yaml")
    return True


def main():
    """Main setup function."""
    print("🚀 Setting up GitHub Context Extraction Workflow")
    print("=" * 50)

    # Check Python version
    if not check_python_version():
        sys.exit(1)

    # Create directories
    create_directories()

    # Install dependencies
    if not install_dependencies():
        print("❌ Setup failed during dependency installation")
        sys.exit(1)

    # Create sample configuration
    if not create_sample_config():
        print("❌ Setup failed during configuration creation")
        sys.exit(1)

    # Check GitHub token
    check_github_token()

    print("\n✅ Setup completed successfully!")
    print("\n📝 Next steps:")
    print("1. Set your GitHub token: export GITHUB_TOKEN='your-token'")
    print("2. Edit configuration: config/settings.yaml")
    print("3. Run discovery: python main.py discover")
    print("4. Review the generated CSV file")
    print("5. Run extraction: python main.py extract <review-file>")


if __name__ == "__main__":
    main()

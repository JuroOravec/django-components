# GitHub Context Extraction Workflow

A comprehensive workflow for extracting GitHub discussions, PRs, and issues into your codebase to provide better context for LLM agents. This tool is designed to work with LLM IDEs like Cursor that don't handle GitHub discussions well.

## Features

- **Time-bound extraction**: Extract content from a specific date range (e.g., start of 2024 to now)
- **Multi-repository support**: Process multiple repositories in a single workflow
- **Manual review workflow**: Review and approve/reject content before extraction
- **Comment tracking**: Detect updates to comments and posts
- **Manual content addition**: Add custom PRs/issues/discussions manually
- **Weekly automation**: Designed to run weekly for continuous updates
- **Comprehensive summaries**: Generate design understanding summaries
- **Type-safe configuration**: Full Pydantic validation and type checking

## Architecture

The workflow consists of several modular components:

```
github-context/
├── src/                    # Source code
│   ├── config.py          # Pydantic configuration models
│   ├── models.py          # Data models for GitHub content
│   ├── github_client.py   # GitHub API client with rate limiting
│   ├── processor.py       # Content processing and cleaning
│   ├── storage.py         # File storage and management
│   ├── orchestrator.py    # Main workflow orchestration
│   └── cli.py            # Command-line interface
├── config/                # Configuration files
│   └── settings.yaml     # Main configuration
├── data/                  # Extracted content storage
├── scripts/               # Utility scripts
└── requirements.txt       # Python dependencies
```

## Installation

1. **Clone and setup**:

   ```bash
   cd github-context
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Set up GitHub token**:

   ```bash
   export GITHUB_TOKEN="your-github-personal-access-token"
   ```

3. **Initialize configuration**:
   ```bash
   python -m src.cli init
   ```

## Configuration

The configuration uses Pydantic models for type safety and validation. Edit `config/settings.yaml`:

```yaml
# GitHub API Configuration
github:
  token: "${GITHUB_TOKEN}"
  rate_limit: 5000
  api_url: "https://api.github.com"

# Repository Configuration
repositories:
  - owner: "django-components"
    name: "django-components"
    description: "Main repository"

# Time Range Configuration
time_range:
  start_date: "2024-01-01"
  end_date: "now"
  timezone: "UTC"

# Content Types Configuration
content_types:
  pull_requests: true
  issues: true
  discussions: true
  comments: true
  include_closed: true
  include_draft_prs: true

# Review and Filtering Configuration
review:
  default_action: "review"
  auto_approve_authors: []
  auto_reject_labels: ["spam", "bot"]
  min_comment_length: 10

# Output Configuration
output:
  data_dir: "data"
  review_format: "csv"
  compress_files: true
```

## Usage

### Basic Workflow

1. **Discover content**:

   ```bash
   python -m src.cli discover
   ```

2. **Extract and generate review data**:

   ```bash
   python -m src.cli extract
   ```

3. **Review content**:

   ```bash
   python -m src.cli review
   ```

4. **Extract approved content**:
   ```bash
   python -m src.cli run --review-file data/review_data.csv
   ```

### Advanced Commands

- **Check status**:

  ```bash
  python -m src.cli status
  ```

- **Clean up old files**:

  ```bash
  python -m src.cli cleanup --days 30
  ```

- **Initialize new configuration**:
  ```bash
  python -m src.cli init --output custom-data-dir
  ```

## Weekly Automation

Set up a cron job or GitHub Action to run weekly:

```bash
# Weekly update script
python -m src.cli extract
python -m src.cli run --review-file data/latest_review.csv
```

## Output Structure

Extracted content is organized as follows:

```
data/
├── raw/                    # Raw API responses
├── processed/              # Cleaned and processed content
├── metadata/               # Review and metadata files
├── summaries/              # Generated summaries
└── review_data.csv         # Review spreadsheet
```

## Configuration Validation

The configuration system provides:

- **Type validation**: All configuration values are validated against their expected types
- **Required field checking**: Missing required fields are caught early
- **Value validation**: Date formats, enum values, and other constraints are enforced
- **Default values**: Sensible defaults for optional settings
- **Documentation**: Each field includes descriptive help text

## API Reference

### Configuration Models

- `ExtractionConfig`: Main configuration container
- `GitHubConfig`: GitHub API settings
- `RepositoryConfig`: Repository information
- `TimeRangeConfig`: Date range settings
- `ContentTypesConfig`: Content type filters
- `ReviewConfig`: Review and filtering rules
- `OutputConfig`: Output settings
- `ProcessingConfig`: Content processing options
- `LoggingConfig`: Logging configuration
- `AdvancedConfig`: Advanced settings

### Data Models

- `GitHubContent`: Base content model
- `PullRequest`: Pull request specific data
- `Issue`: Issue specific data
- `Discussion`: Discussion specific data
- `ContentCollection`: Collection of content items
- `ReviewStatus`: Review status enumeration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

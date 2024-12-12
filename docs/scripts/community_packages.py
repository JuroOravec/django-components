from functools import lru_cache
import requests
from typing import Any, Dict, List, Optional, TypedDict
# from jinja2 import Environment, FileSystemLoader


# Constants
PYPI_BASE_URL = "https://pypi.org/pypi"
STATIC_ADD = ["djc-plugin-example", "djc-plugin-another"]
STATIC_EXCLUDE = ["djc-plugin-skip"]


class PypiIndexResponse(TypedDict):
    projects: List["PypiIndexEntry"]
    meta: Dict[str, str]


class PypiIndexEntry(TypedDict):
    name: str


class PypiProjectResponse(TypedDict):
    info: "PypiProjectDetails"
    # We don't care about the fields below
    last_serial: int
    releases: Any
    urls: List
    vulnerabilities: List


class PypiProjectDetails(TypedDict):
    author: Optional[str]
    # May have format `John Smith <john.smith@myemail.com>`
    author_email: Optional[str]
    maintainer: Optional[str]
    # May have format `John Smith <john.smith@myemail.com>`
    maintainer_email: Optional[str]

    name: str
    # E.g. 'A way to create simple reusable template components in Django.'
    summary: str
    # E.g. '0.116'
    version: str
    # E.g. 'https://pypi.org/project/django-components/'
    package_url: str
    # E.g. 'https://pypi.org/project/django-components/'
    project_url: str
    project_urls: Dict[str, str]
    release_url: str
    bugtrack_url: Optional[str]
    description: Optional[str]
    description_content_type: Optional[str]
    docs_url: Optional[str]
    download_url: Optional[str]
    downloads: Dict[str, int]
    home_page: Optional[str]
    # E.g. 'django, components, css, js, html'
    keywords: Optional[str]
    classifiers: List[str]
    # E.g. 'MIT'
    license: Optional[str]
    # E.g. '['Django>=4.2', 'selectolax>=0.3.24']'
    requires_dist: List[str]
    # E.g. '<4.0,>=3.8'
    requires_python: str
    yanked: bool


@lru_cache()
def download_pypi_index() -> List[PypiIndexEntry]:
    response = requests.get("https://pypi.org/simple/", headers={"Accept": "application/vnd.pypi.simple.v1+json"})
    if response.status_code != 200:
        raise Exception(f"Failed to fetch PyPI packages: {response.status_code}")

    data: PypiIndexResponse = response.json()
    return data["projects"]


def search_pypi(prefix: str) -> List[str]:
    """Search for packages on PyPI starting with a prefix."""
    pypi_index = download_pypi_index()

    # Filter package names from the simple index
    return [pkg["name"] for pkg in pypi_index if pkg["name"].startswith(prefix)]


def get_metadata(package_name):
    """Fetch metadata for a PyPI package."""
    response = requests.get(f"{PYPI_BASE_URL}/{package_name}/json")
    if response.status_code != 200:
        print(f"Failed to fetch metadata for {package_name}. Skipping...")
        return None
    data: PypiProjectResponse = response.json()

    info = data.get("info", {})
    del info["description"]
    del info["classifiers"]

    # NOTE: Maintainer info may include the name, having a format
    # `John Smith <john.smith@myemail.com>`
    def name_from_email(email: Optional[str]) -> Optional[str]:
        if email and "<" in email:
            return email.rsplit("<", 1)[0].strip()
        return None

    # Preferably show maintainer, assumming that maintainr is active whereas author may not be
    author_or_maintainer = None
    if info.get("maintainer", None):
        author_or_maintainer = info["maintainer"]
    elif info.get("maintainer_email", None):
        author_or_maintainer = name_from_email(info["maintainer_email"])
    elif info.get("author", None):
        author_or_maintainer = info["author"]
    elif info.get("author_email", None):
        author_or_maintainer = name_from_email(info["author_email"])

    return {
        "name": info.get("name"),
        "version": info.get("version"),
        "author_or_maintainer": author_or_maintainer,
        "summary": info.get("summary"),
        "home_page": info.get("home_page"),
        "keywords": info.get("keywords"),
        "package_url": info.get("package_url"),
        "license": info.get("license"),
    }


def render_html(packages, output_file="output.html"):
    """Generate an HTML file with package info cards."""
    env = Environment(loader=FileSystemLoader(searchpath="."), autoescape=True)
    template_str = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PyPI Package Search</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .card { border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin: 10px 0; }
            .card h2 { margin: 0; font-size: 1.2em; }
            .card p { margin: 5px 0; }
            .card a { color: #007BFF; text-decoration: none; }
        </style>
    </head>
    <body>
        <h1>Matched PyPI Packages</h1>
        {% for pkg in packages %}
        <div class="card">
            <h2><a href="{{ pkg.package_url }}" target="_blank">{{ pkg.name }}</a></h2>
            <p><strong>Version:</strong> {{ pkg.version }}</p>
            <p><strong>Author:</strong> {{ pkg.author }}</p>
            <p><strong>Summary:</strong> {{ pkg.summary }}</p>
            <a href="{{ pkg.home_page }}" target="_blank">Project Homepage</a>
        </div>
        {% endfor %}
    </body>
    </html>
    """
    template = env.from_string(template_str)
    with open(output_file, "w") as f:
        f.write(template.render(packages=packages))

def main():
    prefix = "djc-plugin-"
    print(f"Searching for packages with prefix '{prefix}'...")
    
    # Search PyPI
    found_packages = search_pypi(prefix)
    
    # Curate the results - Add extra or remove undesirable packages
    all_packages = list(set(found_packages + STATIC_ADD) - set(STATIC_EXCLUDE))
    
    print(f"Found {len(all_packages)} packages after filtering.")
    
    # Step 2: Get metadata for each package
    package_details = []
    for package in all_packages:
        print(f"Fetching metadata for {package}...")
        metadata = get_metadata(package)
        if metadata:
            package_details.append(metadata)
    
    # Step 3: Render HTML
    output_file = "pypi_packages.html"
    render_html(package_details, output_file)
    print(f"HTML file generated: {output_file}")

# TODO
# if __name__ == "__main__":
# main()


pypi_index = download_pypi_index()
print(search_pypi("dc-"))

print(get_metadata("django-components"))

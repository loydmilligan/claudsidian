"""GitHub repository extractor using GitHub API.

This module extracts repository metadata and README content from GitHub URLs
without authentication (using public API endpoints).
"""

import base64
import logging
import re
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


# Common framework/library detection patterns
FRAMEWORK_PATTERNS = {
    "react": ["react", "react-dom", "next.js", "nextjs", "gatsby"],
    "vue": ["vue", "vuex", "nuxt", "nuxt.js"],
    "angular": ["angular", "@angular/core"],
    "svelte": ["svelte", "sveltekit"],
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi"],
    "express": ["express"],
    "rails": ["rails", "ruby on rails"],
    "spring": ["spring", "spring-boot", "springboot"],
    "laravel": ["laravel"],
    "tensorflow": ["tensorflow", "tf"],
    "pytorch": ["pytorch", "torch"],
    "docker": ["docker", "dockerfile", "container"],
    "kubernetes": ["kubernetes", "k8s", "helm"],
}


@dataclass
class GitHubContent:
    """Extracted GitHub repository content.

    Attributes:
        owner: Repository owner username
        name: Repository name
        full_name: Full repo identifier (owner/name)
        description: Repository description
        stars: Star count
        forks: Fork count
        watchers: Watcher count
        language: Primary programming language
        topics: Repository topics/tags
        license: License name if available
        created_at: Repository creation date (ISO 8601)
        updated_at: Last update date (ISO 8601)
        pushed_at: Last push date (ISO 8601)
        default_branch: Default branch name
        readme_content: README content in markdown
        has_readme: Whether README was found
        source_url: Original GitHub URL
        homepage: Project homepage URL if set
        open_issues: Number of open issues
        tech_tags: Auto-detected technology tags
    """

    owner: str
    name: str
    full_name: str
    description: str
    stars: int
    forks: int
    watchers: int
    language: str | None
    topics: list[str] = field(default_factory=list)
    license: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    pushed_at: str | None = None
    default_branch: str = "main"
    readme_content: str = ""
    has_readme: bool = False
    source_url: str = ""
    homepage: str | None = None
    open_issues: int = 0
    tech_tags: list[str] = field(default_factory=list)


class GitHubExtractor:
    """Extracts content from GitHub repositories.

    Uses GitHub's public REST API to fetch repository metadata and README
    content. No authentication required for public repositories.

    Example:
        >>> extractor = GitHubExtractor()
        >>> repo = await extractor.extract("https://github.com/owner/repo")
        >>> print(f"{repo.full_name}: {repo.stars} stars")
        >>> await extractor.close()
    """

    def __init__(self) -> None:
        """Initialize the GitHub extractor with HTTP client."""
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Claudsidian/1.0",
            },
        )
        self._api_base = "https://api.github.com"

    async def extract(self, url: str) -> GitHubContent:
        """Extract repository content from GitHub URL.

        Args:
            url: GitHub repository URL

        Returns:
            GitHubContent with repository metadata and README

        Raises:
            ValueError: If URL is not a valid GitHub repository URL
            httpx.HTTPError: If API request fails
        """
        owner, repo = self._parse_github_url(url)
        if not owner or not repo:
            raise ValueError(f"Could not parse GitHub repository from URL: {url}")

        logger.info(f"Extracting GitHub repo: {owner}/{repo}")

        # Fetch repository metadata
        metadata = await self._fetch_metadata(owner, repo)

        # Fetch README content
        readme_content, has_readme = await self._fetch_readme(owner, repo)

        # Extract tech tags from topics, language, and README
        tech_tags = self._extract_tech_tags(
            metadata.get("topics", []),
            metadata.get("language"),
            readme_content
        )

        return GitHubContent(
            owner=owner,
            name=repo,
            full_name=f"{owner}/{repo}",
            description=metadata.get("description") or "",
            stars=metadata.get("stargazers_count", 0),
            forks=metadata.get("forks_count", 0),
            watchers=metadata.get("watchers_count", 0),
            language=metadata.get("language"),
            topics=metadata.get("topics", []),
            license=metadata.get("license", {}).get("name") if metadata.get("license") else None,
            created_at=metadata.get("created_at"),
            updated_at=metadata.get("updated_at"),
            pushed_at=metadata.get("pushed_at"),
            default_branch=metadata.get("default_branch", "main"),
            readme_content=readme_content,
            has_readme=has_readme,
            source_url=url,
            homepage=metadata.get("homepage"),
            open_issues=metadata.get("open_issues_count", 0),
            tech_tags=tech_tags,
        )

    def _parse_github_url(self, url: str) -> tuple[str | None, str | None]:
        """Parse GitHub URL to extract owner and repo name.

        Supports various GitHub URL formats:
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - https://github.com/owner/repo/tree/branch
        - https://github.com/owner/repo/blob/branch/path
        - git@github.com:owner/repo.git

        Args:
            url: GitHub URL

        Returns:
            Tuple of (owner, repo) or (None, None) if parsing fails
        """
        # HTTPS format
        https_pattern = r"github\.com/([^/]+)/([^/\.]+)"
        match = re.search(https_pattern, url)
        if match:
            return match.group(1), match.group(2)

        # SSH format (git@github.com:owner/repo.git)
        ssh_pattern = r"github\.com:([^/]+)/([^/\.]+)"
        match = re.search(ssh_pattern, url)
        if match:
            return match.group(1), match.group(2)

        return None, None

    async def _fetch_metadata(self, owner: str, repo: str) -> dict:
        """Fetch repository metadata from GitHub API.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Dictionary with repository metadata

        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self._api_base}/repos/{owner}/{repo}"
        response = await self._client.get(url)
        response.raise_for_status()
        return response.json()

    async def _fetch_readme(self, owner: str, repo: str) -> tuple[str, bool]:
        """Fetch README content from repository.

        Tries multiple README filenames (README.md, readme.md, etc.).

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Tuple of (readme_content, has_readme)
        """
        url = f"{self._api_base}/repos/{owner}/{repo}/readme"

        try:
            response = await self._client.get(url)
            response.raise_for_status()
            data = response.json()

            # README content is base64 encoded
            content_b64 = data.get("content", "")
            if content_b64:
                # GitHub API returns content with newlines, need to strip them
                content_b64 = content_b64.replace("\n", "")
                readme_content = base64.b64decode(content_b64).decode("utf-8")
                logger.info(f"Found README ({len(readme_content)} chars)")
                return readme_content, True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.info("No README found")
            else:
                logger.warning(f"Error fetching README: {e}")
        except Exception as e:
            logger.warning(f"Error decoding README: {e}")

        return "", False

    def _extract_tech_tags(
        self,
        topics: list[str],
        language: str | None,
        readme: str
    ) -> list[str]:
        """Extract technology tags from repo metadata and content.

        Analyzes topics, primary language, and README content to generate
        relevant technology tags.

        Args:
            topics: GitHub repository topics
            language: Primary programming language
            readme: README content

        Returns:
            List of technology tags
        """
        tags = set()

        # Add primary language as tag
        if language:
            tags.add(language.lower())

        # Add topics as tags
        for topic in topics:
            tags.add(topic.lower())

        # Detect frameworks and libraries from README
        readme_lower = readme.lower()
        for framework, keywords in FRAMEWORK_PATTERNS.items():
            for keyword in keywords:
                if keyword in readme_lower:
                    tags.add(framework)
                    break

        # Clean up and sort tags
        cleaned_tags = sorted([tag for tag in tags if tag and len(tag) < 30])

        logger.info(f"Extracted {len(cleaned_tags)} tech tags")
        return cleaned_tags

    async def close(self) -> None:
        """Close the HTTP client.

        Should be called when done using the extractor to cleanup resources.
        """
        await self._client.aclose()

    async def __aenter__(self) -> "GitHubExtractor":
        """Support async context manager protocol."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Support async context manager protocol."""
        await self.close()

"""URL parsing utilities for extracting and validating URL components."""

import re
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlunparse


def extract_domain(url: str) -> str:
    """
    Extract the domain from a URL.

    Args:
        url: The URL to extract the domain from

    Returns:
        The domain (netloc) of the URL

    Raises:
        ValueError: If the URL is invalid or doesn't contain a domain

    Examples:
        >>> extract_domain("https://www.example.com/path")
        'www.example.com'
        >>> extract_domain("http://subdomain.example.com:8080/path")
        'subdomain.example.com:8080'
    """
    if not url:
        raise ValueError("URL cannot be empty")

    # Add scheme if missing to help urlparse
    if not url.startswith(("http://", "https://", "//")):
        url = f"https://{url}"

    parsed = urlparse(url)
    domain = parsed.netloc

    if not domain:
        raise ValueError(f"No domain found in URL: {url}")

    return domain


def extract_youtube_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from YouTube URLs.

    Supports the following URL formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    - https://m.youtube.com/watch?v=VIDEO_ID

    Args:
        url: The YouTube URL to extract the video ID from

    Returns:
        The video ID if found, None otherwise

    Examples:
        >>> extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
        >>> extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
        >>> extract_youtube_video_id("https://example.com")
        None
    """
    if not url:
        return None

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Check if it's a YouTube domain
        youtube_domains = [
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "youtu.be",
        ]

        if not any(domain == yt_domain for yt_domain in youtube_domains):
            return None

        # Handle youtu.be format
        if domain == "youtu.be":
            # Video ID is the path without leading slash
            video_id = parsed.path.lstrip("/").split("/")[0].split("?")[0]
            if video_id and len(video_id) == 11:  # YouTube video IDs are 11 chars
                return video_id
            return None

        # Handle youtube.com/watch?v=VIDEO_ID format
        if parsed.path == "/watch":
            query_params = parse_qs(parsed.query)
            video_ids = query_params.get("v", [])
            if video_ids and video_ids[0]:
                return video_ids[0]
            return None

        # Handle youtube.com/embed/VIDEO_ID and youtube.com/v/VIDEO_ID formats
        if parsed.path.startswith("/embed/") or parsed.path.startswith("/v/"):
            video_id = parsed.path.split("/")[2].split("?")[0]
            if video_id and len(video_id) == 11:
                return video_id
            return None

        return None

    except Exception:
        return None


def extract_github_repo(url: str) -> Optional[tuple[str, str]]:
    """
    Extract (owner, repo) from GitHub URLs.

    Supports the following URL formats:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - https://github.com/owner/repo/tree/branch
    - https://github.com/owner/repo/issues/123
    - git@github.com:owner/repo.git

    Args:
        url: The GitHub URL to extract the owner and repo from

    Returns:
        A tuple of (owner, repo) if found, None otherwise

    Examples:
        >>> extract_github_repo("https://github.com/torvalds/linux")
        ('torvalds', 'linux')
        >>> extract_github_repo("https://github.com/microsoft/vscode.git")
        ('microsoft', 'vscode')
        >>> extract_github_repo("https://example.com")
        None
    """
    if not url:
        return None

    try:
        # Handle git@github.com:owner/repo.git format
        git_ssh_pattern = r"git@github\.com:([^/]+)/(.+?)(?:\.git)?$"
        match = re.match(git_ssh_pattern, url)
        if match:
            owner, repo = match.groups()
            return (owner, repo)

        # Handle HTTPS URLs
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Check if it's a GitHub domain
        if domain not in ["github.com", "www.github.com"]:
            return None

        # Parse the path
        path_parts = [p for p in parsed.path.split("/") if p]

        # Need at least owner and repo
        if len(path_parts) < 2:
            return None

        owner = path_parts[0]
        repo = path_parts[1]

        # Remove .git suffix if present
        if repo.endswith(".git"):
            repo = repo[:-4]

        # Basic validation: owner and repo should not be empty and should be alphanumeric-ish
        if owner and repo and re.match(r"^[\w\-\.]+$", owner) and re.match(r"^[\w\-\.]+$", repo):
            return (owner, repo)

        return None

    except Exception:
        return None


def is_valid_url(url: str) -> bool:
    """
    Check if URL is a valid HTTP/HTTPS URL.

    Args:
        url: The URL to validate

    Returns:
        True if the URL is valid, False otherwise

    Examples:
        >>> is_valid_url("https://www.example.com")
        True
        >>> is_valid_url("http://localhost:8080/path")
        True
        >>> is_valid_url("ftp://example.com")
        False
        >>> is_valid_url("not a url")
        False
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url)

        # Must have HTTP or HTTPS scheme
        if parsed.scheme not in ["http", "https"]:
            return False

        # Must have a netloc (domain)
        if not parsed.netloc:
            return False

        # Basic domain validation - should contain at least one dot or be localhost
        domain = parsed.netloc.split(":")[0]  # Remove port if present
        if domain != "localhost" and "." not in domain:
            return False

        return True

    except Exception:
        return False


def normalize_url(url: str) -> str:
    """
    Normalize URL by applying consistent formatting rules.

    Normalization steps:
    1. Lowercase the scheme and domain
    2. Remove trailing slashes from path (except for root path)
    3. Remove default ports (80 for HTTP, 443 for HTTPS)
    4. Remove empty query strings and fragments

    Args:
        url: The URL to normalize

    Returns:
        The normalized URL

    Raises:
        ValueError: If the URL is invalid

    Examples:
        >>> normalize_url("HTTPS://WWW.EXAMPLE.COM/Path/")
        'https://www.example.com/Path'
        >>> normalize_url("http://example.com:80/")
        'http://example.com/'
        >>> normalize_url("https://example.com:443/path?")
        'https://example.com/path'
    """
    if not url:
        raise ValueError("URL cannot be empty")

    try:
        parsed = urlparse(url)

        # Lowercase scheme and netloc
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Remove default ports
        if netloc.endswith(":80") and scheme == "http":
            netloc = netloc[:-3]
        elif netloc.endswith(":443") and scheme == "https":
            netloc = netloc[:-4]

        # Handle path
        path = parsed.path
        if path and path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        elif not path:
            path = "/"

        # Remove empty query and fragment
        query = parsed.query if parsed.query else ""
        fragment = parsed.fragment if parsed.fragment else ""

        # Reconstruct URL
        normalized = urlunparse((
            scheme,
            netloc,
            path,
            parsed.params,
            query,
            fragment
        ))

        return normalized

    except Exception as e:
        raise ValueError(f"Invalid URL: {url}") from e

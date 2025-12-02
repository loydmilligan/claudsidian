"""3D printable model extractor for Thingiverse, Printables, and Cults3D.

This module extracts metadata from 3D model hosting sites including:
- Model name and description
- Creator information
- File types available (STL, OBJ, 3MF, etc.)
- Print settings (material, layer height, supports, infill)
- Tags and categories
- Download/like counts
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from src.utils.url import extract_domain

logger = logging.getLogger(__name__)


@dataclass
class PrintSettings:
    """Recommended print settings for a 3D model.

    Attributes:
        material: Recommended filament material (PLA, PETG, ABS, etc.)
        layer_height: Recommended layer height in mm
        infill: Recommended infill percentage
        supports: Whether supports are needed
        raft: Whether a raft is recommended
        resolution: Print resolution (low, medium, high)
        nozzle_size: Recommended nozzle diameter in mm
        print_time: Estimated print time
        notes: Additional print notes
    """

    material: Optional[str] = None
    layer_height: Optional[float] = None
    infill: Optional[int] = None
    supports: Optional[bool] = None
    raft: Optional[bool] = None
    resolution: Optional[str] = None
    nozzle_size: Optional[float] = None
    print_time: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class PrintableContent:
    """Extracted 3D printable model content.

    Attributes:
        title: Model name/title
        description: Model description
        creator: Creator/designer username
        creator_url: Link to creator's profile
        source_url: Original URL
        platform: Platform name (Thingiverse, Printables, Cults3D)
        file_types: Available file formats
        download_count: Number of downloads
        like_count: Number of likes/makes
        print_settings: Recommended print settings
        tags: Model tags/categories
        images: URLs to model images
        license: License type if specified
        remix_of: URL of original if this is a remix
        publish_date: When the model was published
    """

    title: str
    description: str
    creator: str
    source_url: str
    platform: str
    file_types: list[str] = field(default_factory=list)
    download_count: Optional[int] = None
    like_count: Optional[int] = None
    print_settings: PrintSettings = field(default_factory=PrintSettings)
    tags: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    creator_url: Optional[str] = None
    license: Optional[str] = None
    remix_of: Optional[str] = None
    publish_date: Optional[str] = None


class PrintableExtractor:
    """Extracts 3D model information from printable hosting sites.

    Supports:
    - Thingiverse (thingiverse.com)
    - Printables (printables.com)
    - Cults3D (cults3d.com)

    Example:
        >>> extractor = PrintableExtractor()
        >>> model = await extractor.extract("https://www.thingiverse.com/thing:12345")
        >>> print(f"{model.title} by {model.creator}")
        >>> await extractor.close()
    """

    def __init__(self) -> None:
        """Initialize the printable extractor with an HTTP client."""
        self._client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )

    async def extract(self, url: str) -> PrintableContent:
        """Extract 3D model content from URL.

        Args:
            url: The URL to extract content from

        Returns:
            PrintableContent object with extracted data

        Raises:
            httpx.HTTPError: If the HTTP request fails
            ValueError: If the URL is not from a supported platform
        """
        domain = extract_domain(url).lower().replace("www.", "")

        if "thingiverse.com" in domain:
            return await self._extract_thingiverse(url)
        elif "printables.com" in domain:
            return await self._extract_printables(url)
        elif "cults3d.com" in domain:
            return await self._extract_cults3d(url)
        else:
            raise ValueError(f"Unsupported platform: {domain}")

    async def _extract_thingiverse(self, url: str) -> PrintableContent:
        """Extract from Thingiverse.

        Args:
            url: Thingiverse URL

        Returns:
            PrintableContent with extracted data
        """
        response = await self._client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Title
        title = self._get_text(soup, "h1") or "Untitled Model"

        # Description
        description = ""
        desc_elem = soup.select_one(".ThingPage__description, .thing-description")
        if desc_elem:
            description = desc_elem.get_text(strip=True)

        # Creator
        creator = "Unknown"
        creator_url = None
        creator_elem = soup.select_one(
            ".ThingPage__createdBy a, .thing-header-data a[href*='/users/']"
        )
        if creator_elem:
            creator = creator_elem.get_text(strip=True)
            creator_url = creator_elem.get("href")
            if creator_url and not creator_url.startswith("http"):
                creator_url = "https://www.thingiverse.com" + creator_url

        # Stats
        download_count = self._extract_number(soup, ".thing-file-downloads")
        like_count = self._extract_number(soup, ".thing-likes")

        # File types (from download section)
        file_types = self._extract_file_types(soup, ".thing-files")

        # Tags
        tags = []
        for tag_elem in soup.select(".thing-tags a, .tags a"):
            tag_text = tag_elem.get_text(strip=True)
            if tag_text:
                tags.append(tag_text.lower().replace(" ", "-"))

        # Print settings
        print_settings = self._extract_print_settings_from_html(soup, response.text)

        # Images
        images = []
        for img in soup.select(".thing-image img, .ThingPage__galleryImage img"):
            src = img.get("src") or img.get("data-src")
            if src:
                images.append(src)

        # License
        license_text = None
        license_elem = soup.select_one(".thing-license, .license")
        if license_elem:
            license_text = license_elem.get_text(strip=True)

        # Publish date
        publish_date = None
        date_elem = soup.select_one("time[datetime]")
        if date_elem:
            publish_date = date_elem.get("datetime")

        return PrintableContent(
            title=title,
            description=description,
            creator=creator,
            creator_url=creator_url,
            source_url=url,
            platform="Thingiverse",
            file_types=file_types,
            download_count=download_count,
            like_count=like_count,
            print_settings=print_settings,
            tags=tags,
            images=images[:5],  # Limit images
            license=license_text,
            publish_date=publish_date,
        )

    async def _extract_printables(self, url: str) -> PrintableContent:
        """Extract from Printables (Prusa).

        Args:
            url: Printables URL

        Returns:
            PrintableContent with extracted data
        """
        response = await self._client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Title
        title = self._get_text(soup, "h1") or "Untitled Model"

        # Description
        description = ""
        desc_elem = soup.select_one(".model-description, [class*='description']")
        if desc_elem:
            description = desc_elem.get_text(strip=True)

        # Creator
        creator = "Unknown"
        creator_url = None
        creator_elem = soup.select_one("a[href*='/social/']")
        if creator_elem:
            creator = creator_elem.get_text(strip=True)
            creator_url = creator_elem.get("href")
            if creator_url and not creator_url.startswith("http"):
                creator_url = "https://www.printables.com" + creator_url

        # Stats - Printables uses different structure
        download_count = self._extract_number(soup, "[class*='downloads']")
        like_count = self._extract_number(soup, "[class*='likes']")

        # File types
        file_types = self._extract_file_types(soup, ".files, [class*='files']")

        # Tags
        tags = []
        for tag_elem in soup.select("a[href*='/tag/'], .tag"):
            tag_text = tag_elem.get_text(strip=True)
            if tag_text:
                tags.append(tag_text.lower().replace(" ", "-"))

        # Print settings
        print_settings = self._extract_print_settings_from_html(soup, response.text)

        # Images
        images = []
        for img in soup.select("img[src*='cdn.'], img[src*='media']"):
            src = img.get("src")
            if src and "thumbnail" not in src:
                images.append(src)

        return PrintableContent(
            title=title,
            description=description,
            creator=creator,
            creator_url=creator_url,
            source_url=url,
            platform="Printables",
            file_types=file_types,
            download_count=download_count,
            like_count=like_count,
            print_settings=print_settings,
            tags=tags,
            images=images[:5],
        )

    async def _extract_cults3d(self, url: str) -> PrintableContent:
        """Extract from Cults3D.

        Args:
            url: Cults3D URL

        Returns:
            PrintableContent with extracted data
        """
        response = await self._client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Title
        title = self._get_text(soup, "h1") or "Untitled Model"

        # Description
        description = ""
        desc_elem = soup.select_one(".creation-page__description, .description")
        if desc_elem:
            description = desc_elem.get_text(strip=True)

        # Creator
        creator = "Unknown"
        creator_url = None
        creator_elem = soup.select_one("a[href*='/en/users/']")
        if creator_elem:
            creator = creator_elem.get_text(strip=True)
            creator_url = creator_elem.get("href")
            if creator_url and not creator_url.startswith("http"):
                creator_url = "https://cults3d.com" + creator_url

        # Stats
        download_count = self._extract_number(soup, ".downloads-count, [class*='download']")
        like_count = self._extract_number(soup, ".likes-count, [class*='like']")

        # File types
        file_types = self._extract_file_types(soup, ".files-list, [class*='files']")

        # Tags
        tags = []
        for tag_elem in soup.select("a[href*='/tags/'], .tag-link"):
            tag_text = tag_elem.get_text(strip=True)
            if tag_text:
                tags.append(tag_text.lower().replace(" ", "-"))

        # Print settings
        print_settings = self._extract_print_settings_from_html(soup, response.text)

        # Images
        images = []
        for img in soup.select(".creation-page__image img, .gallery img"):
            src = img.get("src") or img.get("data-src")
            if src:
                images.append(src)

        # License
        license_text = None
        license_elem = soup.select_one(".license, [class*='license']")
        if license_elem:
            license_text = license_elem.get_text(strip=True)

        return PrintableContent(
            title=title,
            description=description,
            creator=creator,
            creator_url=creator_url,
            source_url=url,
            platform="Cults3D",
            file_types=file_types,
            download_count=download_count,
            like_count=like_count,
            print_settings=print_settings,
            tags=tags,
            images=images[:5],
            license=license_text,
        )

    def _get_text(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """Get text content from a selector."""
        elem = soup.select_one(selector)
        return elem.get_text(strip=True) if elem else None

    def _extract_number(self, soup: BeautifulSoup, selector: str) -> Optional[int]:
        """Extract a number from text in the selected element."""
        elem = soup.select_one(selector)
        if not elem:
            return None

        text = elem.get_text(strip=True)
        # Extract numbers from text like "1.2K downloads" or "500"
        numbers = re.findall(r"[\d,\.]+[kKmM]?", text)
        if not numbers:
            return None

        num_str = numbers[0].replace(",", "")
        multiplier = 1

        if num_str.endswith(("k", "K")):
            multiplier = 1000
            num_str = num_str[:-1]
        elif num_str.endswith(("m", "M")):
            multiplier = 1000000
            num_str = num_str[:-1]

        try:
            return int(float(num_str) * multiplier)
        except ValueError:
            return None

    def _extract_file_types(self, soup: BeautifulSoup, selector: str) -> list[str]:
        """Extract file types from download section."""
        file_types = set()
        container = soup.select_one(selector)

        if container:
            text = container.get_text().lower()
        else:
            text = soup.get_text().lower()

        # Common 3D file formats
        formats = ["stl", "obj", "3mf", "step", "stp", "iges", "igs", "f3d", "scad", "blend", "gcode"]

        for fmt in formats:
            if fmt in text or f".{fmt}" in text:
                file_types.add(fmt.upper())

        return list(file_types)

    def _extract_print_settings_from_html(
        self, soup: BeautifulSoup, html: str
    ) -> PrintSettings:
        """Extract print settings from page content.

        Looks for common print setting patterns in the page text and
        structured data.

        Args:
            soup: BeautifulSoup object
            html: Raw HTML text

        Returns:
            PrintSettings object with extracted values
        """
        settings = PrintSettings()
        text = soup.get_text().lower()

        # Material detection
        materials = {
            "pla": ["pla", "polylactic"],
            "petg": ["petg", "pet-g"],
            "abs": ["abs"],
            "tpu": ["tpu", "flexible", "flex"],
            "nylon": ["nylon", "pa"],
            "resin": ["resin", "sla"],
            "asa": ["asa"],
        }

        for material, keywords in materials.items():
            for keyword in keywords:
                if keyword in text:
                    settings.material = material.upper()
                    break
            if settings.material:
                break

        # Layer height
        layer_patterns = [
            r"(\d+\.?\d*)\s*mm\s*layer",
            r"layer\s*height[:\s]*(\d+\.?\d*)",
            r"(\d+\.?\d*)\s*mm\s*nozzle",
        ]
        for pattern in layer_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    settings.layer_height = float(match.group(1))
                    break
                except ValueError:
                    pass

        # Infill
        infill_match = re.search(r"(\d+)\s*%?\s*infill", text)
        if infill_match:
            try:
                settings.infill = int(infill_match.group(1))
            except ValueError:
                pass

        # Supports
        if "no support" in text or "supports: no" in text or "without support" in text:
            settings.supports = False
        elif "support" in text and ("required" in text or "needed" in text or "yes" in text):
            settings.supports = True

        # Raft
        if "no raft" in text or "raft: no" in text:
            settings.raft = False
        elif "raft" in text and ("required" in text or "recommended" in text):
            settings.raft = True

        # Print time
        time_match = re.search(r"print\s*time[:\s]*(\d+\s*(?:hours?|hrs?|h|minutes?|mins?|m))", text)
        if time_match:
            settings.print_time = time_match.group(1)

        return settings

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        """Support async context manager protocol."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Support async context manager protocol."""
        await self.close()

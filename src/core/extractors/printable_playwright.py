"""Playwright-based 3D printable model extractor.

Uses Playwright to capture screenshots and extract content from
JavaScript-heavy 3D model hosting sites like Thingiverse, Printables, and Cults3D.

The screenshots are passed to a vision AI to extract metadata since
these sites render content dynamically.
"""

import asyncio
import base64
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.utils.url import extract_domain

logger = logging.getLogger(__name__)

# Check for playwright availability
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Install with: pip install playwright && playwright install chromium")


@dataclass
class PrintableScreenshots:
    """Screenshots captured from a printable model page."""
    main_image: bytes  # Main model view screenshot
    main_image_path: Optional[Path] = None  # Path where screenshot is saved
    files_image: Optional[bytes] = None  # Files tab screenshot
    files_image_path: Optional[Path] = None
    details_image: Optional[bytes] = None  # Details/settings screenshot
    details_image_path: Optional[Path] = None


@dataclass
class PlaywrightPrintableContent:
    """Content extracted via Playwright + Vision AI.

    Attributes:
        title: Model name/title (from vision AI)
        description: Model description (from vision AI)
        creator: Creator/designer username (from vision AI)
        source_url: Original URL
        platform: Platform name (Thingiverse, Printables, Cults3D)
        screenshots: Captured screenshots
        file_list: List of available files (from vision AI)
        tags: Model tags (from vision AI)
        print_settings: Print settings as text (from vision AI)
        ai_summary: Full summary from vision AI
        captured_at: When the capture was performed
    """
    title: str
    description: str
    source_url: str
    platform: str
    screenshots: PrintableScreenshots
    creator: str = "Unknown"
    file_list: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    print_settings: str = ""
    ai_summary: str = ""
    captured_at: datetime = field(default_factory=datetime.now)


class PlaywrightPrintableExtractor:
    """Extracts 3D model information using Playwright screenshots + Vision AI.

    This extractor:
    1. Launches a headless browser
    2. Navigates to the model page
    3. Takes screenshots of key sections
    4. Passes screenshots to vision AI for content extraction
    5. Saves screenshots to vault assets folder

    Supports:
    - Thingiverse (thingiverse.com)
    - Printables (printables.com)
    - Cults3D (cults3d.com)
    - MakerWorld (makerworld.com)

    Example:
        >>> extractor = PlaywrightPrintableExtractor(vault_path)
        >>> content = await extractor.extract("https://www.printables.com/model/12345")
        >>> print(f"{content.title} - {content.ai_summary}")
        >>> await extractor.close()
    """

    def __init__(self, vault_path: Path, headless: bool = False):
        """Initialize the Playwright extractor.

        Args:
            vault_path: Path to Obsidian vault (for saving screenshots)
            headless: Run browser in headless mode (default True)
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright not installed. Install with:\n"
                "  pip install playwright\n"
                "  playwright install chromium"
            )

        self._vault_path = vault_path
        self._headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None

        # Ensure assets folder exists
        self._assets_path = vault_path / "assets" / "printables"
        self._assets_path.mkdir(parents=True, exist_ok=True)

    async def _ensure_browser(self) -> Browser:
        """Ensure browser is launched."""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self._headless
            )
            logger.info("Playwright browser launched")
        return self._browser

    async def extract(self, url: str) -> PlaywrightPrintableContent:
        """Extract 3D model content using Playwright.

        Args:
            url: The URL to extract content from

        Returns:
            PlaywrightPrintableContent with screenshots and extracted data

        Raises:
            ValueError: If the URL is not from a supported platform
            RuntimeError: If Playwright capture fails
        """
        domain = extract_domain(url).lower().replace("www.", "")

        # Determine platform
        if "thingiverse.com" in domain:
            platform = "Thingiverse"
        elif "printables.com" in domain:
            platform = "Printables"
        elif "cults3d.com" in domain:
            platform = "Cults3D"
        elif "makerworld.com" in domain:
            platform = "MakerWorld"
        else:
            raise ValueError(f"Unsupported platform: {domain}")

        browser = await self._ensure_browser()
        page = await browser.new_page(
            viewport={"width": 1280, "height": 900}
        )

        try:
            logger.info(f"Navigating to {url}")
            # Thingiverse is slow - use longer timeout and domcontentloaded instead of networkidle
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Wait for main content to load
            await self._wait_for_content(page, platform)

            # Take screenshots
            screenshots = await self._capture_screenshots(page, url, platform)

            # Get basic title from page
            title = await page.title() or "Untitled Model"
            # Clean up title (remove site name suffix)
            for suffix in [" - Thingiverse", " - Printables", " - Cults3D", " | MakerWorld"]:
                title = title.replace(suffix, "")

            return PlaywrightPrintableContent(
                title=title.strip(),
                description="",  # Will be filled by vision AI
                source_url=url,
                platform=platform,
                screenshots=screenshots,
            )

        except Exception as e:
            logger.error(f"Playwright extraction failed: {e}")
            raise RuntimeError(f"Failed to capture {url}: {e}")
        finally:
            await page.close()

    async def _wait_for_content(self, page: Page, platform: str) -> None:
        """Wait for platform-specific content to load."""
        try:
            if platform == "Thingiverse":
                await page.wait_for_selector("h1", timeout=10000)
            elif platform == "Printables":
                await page.wait_for_selector("h1", timeout=10000)
            elif platform == "Cults3D":
                await page.wait_for_selector("h1", timeout=10000)
            elif platform == "MakerWorld":
                await page.wait_for_selector("h1", timeout=10000)

            # Extra wait for dynamic content
            await asyncio.sleep(2)
        except Exception as e:
            logger.warning(f"Wait for content timed out: {e}")

    async def _capture_screenshots(
        self,
        page: Page,
        url: str,
        platform: str
    ) -> PrintableScreenshots:
        """Capture screenshots from the page.

        Args:
            page: Playwright page object
            url: Original URL (for generating filename)
            platform: Platform name

        Returns:
            PrintableScreenshots with captured images
        """
        # Generate unique filename based on URL
        url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
        timestamp = datetime.now().strftime("%Y%m%d")
        base_name = f"{platform.lower()}_{url_hash}_{timestamp}"

        # Capture main view
        main_path = self._assets_path / f"{base_name}_main.png"
        main_bytes = await page.screenshot(full_page=False)
        main_path.write_bytes(main_bytes)
        logger.info(f"Saved main screenshot: {main_path}")

        screenshots = PrintableScreenshots(
            main_image=main_bytes,
            main_image_path=main_path
        )

        # Try to capture files tab
        try:
            files_clicked = await self._click_files_tab(page, platform)
            if files_clicked:
                await asyncio.sleep(1.5)
                files_path = self._assets_path / f"{base_name}_files.png"
                files_bytes = await page.screenshot(full_page=False)
                files_path.write_bytes(files_bytes)
                screenshots.files_image = files_bytes
                screenshots.files_image_path = files_path
                logger.info(f"Saved files screenshot: {files_path}")
        except Exception as e:
            logger.warning(f"Could not capture files tab: {e}")

        return screenshots

    async def _click_files_tab(self, page: Page, platform: str) -> bool:
        """Try to click the files/download tab.

        Returns True if successfully clicked, False otherwise.
        """
        selectors = {
            "Thingiverse": ["text=Files", "text=Download", "[data-testid='files-tab']"],
            "Printables": ["text=Files", "text=Download", "button:has-text('Files')"],
            "Cults3D": ["text=Files", "text=Download", ".files-tab"],
            "MakerWorld": ["text=Files", "text=Download"],
        }

        for selector in selectors.get(platform, []):
            try:
                elem = page.locator(selector).first
                if await elem.is_visible(timeout=2000):
                    await elem.click()
                    return True
            except Exception:
                continue

        return False

    def get_relative_image_path(self, absolute_path: Path) -> str:
        """Get vault-relative path for embedding in notes.

        Args:
            absolute_path: Absolute path to image file

        Returns:
            Relative path suitable for Obsidian embed syntax
        """
        try:
            return str(absolute_path.relative_to(self._vault_path))
        except ValueError:
            return str(absolute_path)

    async def close(self) -> None:
        """Close the browser and Playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Playwright browser closed")

    async def __aenter__(self):
        """Support async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Support async context manager."""
        await self.close()

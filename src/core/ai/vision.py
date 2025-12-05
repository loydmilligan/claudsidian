"""Vision AI integration for analyzing images.

Uses Claude's vision capabilities or OpenRouter multimodal models
to extract information from screenshots.
"""

import base64
import logging
from pathlib import Path
from typing import Optional

from src.core.ai.claude import ClaudeClient
from src.core.ai.openrouter import OpenRouterClient, OpenRouterError

logger = logging.getLogger(__name__)


PRINTABLE_VISION_PROMPT = """Analyze this screenshot from a 3D model sharing website and extract the following information.
Be thorough but concise. If information is not visible, say "Not visible".

Extract:
1. **Title**: The model name/title
2. **Creator**: The designer/creator username
3. **Description**: A brief description of what this model is
4. **Files**: List any visible file names (e.g., base.stl, cover.3mf)
5. **Print Settings**: Any visible print settings (material, layer height, infill, supports needed)
6. **Tags/Categories**: Any visible tags or categories
7. **Stats**: Downloads, likes, makes if visible

Format your response as:
TITLE: [title]
CREATOR: [creator name]
DESCRIPTION: [1-2 sentence description]
FILES: [comma-separated list or "Not visible"]
PRINT_SETTINGS: [settings or "Not visible"]
TAGS: [comma-separated tags or "Not visible"]
STATS: [any visible stats or "Not visible"]

SUMMARY: [2-3 sentence summary suitable for a note, describing what this model is and why someone might want to print it]
"""


class VisionAnalyzer:
    """Analyzes images using Claude's vision capabilities or OpenRouter multimodal models.

    Supports:
    - Claude direct API (vision_model="claude")
    - OpenRouter multimodal models (vision_model="qwen/qwen3-vl-32b-instruct", etc.)

    Example:
        >>> analyzer = VisionAnalyzer(claude_api_key=api_key)
        >>> result = await analyzer.analyze_printable_screenshot(screenshot_bytes)
        >>> print(result["title"], result["summary"])

        >>> # Using OpenRouter vision model
        >>> analyzer = VisionAnalyzer(
        ...     openrouter_api_key=key,
        ...     vision_model="qwen/qwen3-vl-32b-instruct"
        ... )
    """

    def __init__(
        self,
        claude_api_key: Optional[str] = None,
        openrouter_api_key: Optional[str] = None,
        vision_model: str = "claude"
    ):
        """Initialize with API keys and vision model selection.

        Args:
            claude_api_key: Anthropic API key (required if vision_model="claude")
            openrouter_api_key: OpenRouter API key (required for OpenRouter models)
            vision_model: Model to use - "claude" for Claude API, or OpenRouter model ID
        """
        self._vision_model = vision_model
        self._claude_client: Optional[ClaudeClient] = None
        self._openrouter_client: Optional[OpenRouterClient] = None

        if vision_model == "claude":
            if not claude_api_key:
                raise ValueError("claude_api_key required when vision_model='claude'")
            self._claude_client = ClaudeClient(claude_api_key)
            logger.info("VisionAnalyzer using Claude direct API")
        else:
            if not openrouter_api_key:
                raise ValueError(f"openrouter_api_key required for vision model: {vision_model}")
            self._openrouter_client = OpenRouterClient(openrouter_api_key, model=vision_model)
            logger.info(f"VisionAnalyzer using OpenRouter model: {vision_model}")

    async def analyze_printable_screenshot(
        self,
        image_data: bytes,
        additional_context: str = ""
    ) -> dict:
        """Analyze a screenshot from a 3D printable site.

        Args:
            image_data: PNG/JPEG image bytes
            additional_context: Optional additional context about the image

        Returns:
            Dict with extracted fields: title, creator, description, files,
            print_settings, tags, stats, summary
        """
        # Encode image as base64
        image_b64 = base64.standard_b64encode(image_data).decode("utf-8")

        # Determine media type (assume PNG for screenshots)
        media_type = "image/png"

        prompt = PRINTABLE_VISION_PROMPT
        if additional_context:
            prompt += f"\n\nAdditional context: {additional_context}"

        try:
            if self._claude_client:
                # Use Claude direct API
                response = await self._claude_client.complete_with_image(
                    prompt=prompt,
                    image_data=image_b64,
                    media_type=media_type,
                    max_tokens=1000,
                    temperature=0.3
                )
                response_content = response.content
            else:
                # Use OpenRouter multimodal API
                response = await self._openrouter_client.complete(
                    prompt=prompt,
                    image_data=image_b64,
                    image_media_type=media_type,
                    max_tokens=1000,
                    temperature=0.3
                )
                response_content = response.content

            return self._parse_response(response_content)

        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return {
                "title": "Unknown",
                "creator": "Unknown",
                "description": "",
                "files": [],
                "print_settings": "",
                "tags": [],
                "stats": "",
                "summary": f"Failed to analyze image: {e}",
                "raw_response": ""
            }

    async def analyze_multiple_screenshots(
        self,
        main_image: bytes,
        files_image: Optional[bytes] = None,
        details_image: Optional[bytes] = None
    ) -> dict:
        """Analyze multiple screenshots and combine results.

        Args:
            main_image: Main model view screenshot
            files_image: Optional files tab screenshot
            details_image: Optional details screenshot

        Returns:
            Combined extracted information
        """
        # Analyze main image first
        result = await self.analyze_printable_screenshot(main_image)

        # If we have a files image, analyze it for file list
        if files_image:
            files_result = await self.analyze_printable_screenshot(
                files_image,
                additional_context="This is the FILES tab. Focus on extracting the list of downloadable files."
            )
            # Merge file list if we got better results
            if files_result.get("files") and files_result["files"] != ["Not visible"]:
                result["files"] = files_result["files"]

        return result

    def _parse_response(self, response_text: str) -> dict:
        """Parse the structured response from vision AI.

        Args:
            response_text: Raw response text

        Returns:
            Dict with parsed fields
        """
        result = {
            "title": "Unknown",
            "creator": "Unknown",
            "description": "",
            "files": [],
            "print_settings": "",
            "tags": [],
            "stats": "",
            "summary": "",
            "raw_response": response_text
        }

        lines = response_text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("TITLE:"):
                result["title"] = line[6:].strip()
            elif line.startswith("CREATOR:"):
                result["creator"] = line[8:].strip()
            elif line.startswith("DESCRIPTION:"):
                result["description"] = line[12:].strip()
            elif line.startswith("FILES:"):
                files_str = line[6:].strip()
                if files_str.lower() != "not visible":
                    result["files"] = [f.strip() for f in files_str.split(",") if f.strip()]
            elif line.startswith("PRINT_SETTINGS:"):
                settings = line[15:].strip()
                if settings.lower() != "not visible":
                    result["print_settings"] = settings
            elif line.startswith("TAGS:"):
                tags_str = line[5:].strip()
                if tags_str.lower() != "not visible":
                    result["tags"] = [t.strip().lower().replace(" ", "-") for t in tags_str.split(",") if t.strip()]
            elif line.startswith("STATS:"):
                stats = line[6:].strip()
                if stats.lower() != "not visible":
                    result["stats"] = stats
            elif line.startswith("SUMMARY:"):
                result["summary"] = line[8:].strip()

        return result

    async def close(self) -> None:
        """Close the client(s)."""
        if self._claude_client:
            await self._claude_client.close()
        if self._openrouter_client:
            await self._openrouter_client.close()

"""Note templates for different content types."""

from src.core.content_type import ContentType


ARTICLE_TEMPLATE = """---
title: "{{ title }}"
source: "{{ source_url }}"
{% if author -%}
author: "{{ author }}"
{% endif -%}
captured: {{ date_captured }}
tags: {{ tags }}
type: article
---

# {{ title }}

> {{ summary }}

## Source
[Original Article]({{ source_url }})
{% if author %}
**Author:** {{ author }}
{% endif %}

## Content
{{ content }}

## Related
{{ backlinks }}
"""

YOUTUBE_TEMPLATE = """---
title: "{{ title }}"
source: "{{ source_url }}"
channel: "{{ channel }}"
{% if duration -%}
duration: {{ duration }}
{% endif -%}
captured: {{ date_captured }}
tags: {{ tags }}
type: video
{% if has_transcript -%}
has_transcript: {{ has_transcript }}
{% endif -%}
---

# {{ title }}

> {{ summary }}

## Video
[![{{ title }}]({{ thumbnail_url }})]({{ source_url }})

**Channel**: [{{ channel }}]({{ channel_url }})
{% if duration_formatted -%}
**Duration**: {{ duration_formatted }}
{% endif -%}
{% if upload_date -%}
**Uploaded**: {{ upload_date }}
{% endif -%}

{% if chapters -%}
## Chapters
{% for chapter in chapters -%}
- [{{ chapter.timestamp }}]({{ source_url }}&t={{ chapter.start_time }}) {{ chapter.title }}
{% endfor -%}
{% endif -%}

{% if key_points -%}
## Key Points
{{ key_points }}
{% endif -%}

{% if transcript_summary -%}
## Transcript Summary
{{ transcript_summary }}
{% endif -%}

## Related
{{ backlinks }}
"""

GITHUB_TEMPLATE = """---
title: "{{ title }}"
source: "{{ source_url }}"
owner: "{{ owner }}"
repo: "{{ repo_name }}"
stars: {{ stars }}
language: "{{ language }}"
captured: {{ date_captured }}
tags: {{ tags }}
type: repo
{% if license -%}
license: "{{ license }}"
{% endif -%}
---

# {{ title }}

> {{ summary }}

## Repository Info

| Metric | Value |
|--------|-------|
| Stars | ⭐ {{ stars }} |
| Forks | 🔱 {{ forks }} |
| Language | {{ language }} |
{% if license -%}
| License | {{ license }} |
{% endif -%}
| Last Updated | {{ updated_at }} |

[View on GitHub]({{ source_url }})
{% if homepage %}
[Project Homepage]({{ homepage }})
{% endif %}

{% if topics -%}
## Topics
{% for topic in topics -%}
`{{ topic }}` {% endfor %}
{% endif -%}

{% if description -%}
## Description
{{ description }}
{% endif -%}

{% if readme_content -%}
## README

{{ readme_content }}
{% endif -%}

## Related
{{ backlinks }}
"""

NEWS_TEMPLATE = """---
title: "{{ title }}"
source: "{{ source_url }}"
source_name: "{{ source_name }}"
{% if publish_date -%}
published: "{{ publish_date }}"
{% endif -%}
{% if author -%}
author: "{{ author }}"
{% endif -%}
{% if section -%}
section: "{{ section }}"
{% endif -%}
captured: {{ date_captured }}
tags: {{ tags }}
type: news
{% if is_breaking -%}
breaking: true
{% endif -%}
---

# {{ title }}

{% if is_breaking -%}
> **BREAKING NEWS**
{% endif -%}

> {{ summary }}

## Source Info

| Field | Value |
|-------|-------|
| Source | **{{ source_name }}** |
{% if publish_date -%}
| Published | {{ publish_date }} |
{% endif -%}
{% if author -%}
| Author | {{ author }} |
{% endif -%}
{% if section -%}
| Section | {{ section }} |
{% endif -%}
{% if last_updated -%}
| Updated | {{ last_updated }} |
{% endif -%}

[Read Original Article]({{ source_url }})

## Content

{{ content }}

## Related
{{ backlinks }}
"""

WALKTHROUGH_TEMPLATE = """---
title: "{{ title }}"
source: "{{ source_url }}"
{% if author -%}
author: "{{ author }}"
{% endif -%}
{% if difficulty -%}
difficulty: "{{ difficulty }}"
{% endif -%}
{% if estimated_time -%}
estimated_time: "{{ estimated_time }}"
{% endif -%}
captured: {{ date_captured }}
tags: {{ tags }}
type: walkthrough
steps_count: {{ steps_count }}
has_code: {{ has_code }}
---

# {{ title }}

{% if difficulty or estimated_time -%}
| Info | Value |
|------|-------|
{% if difficulty -%}
| Difficulty | {{ difficulty }} |
{% endif -%}
{% if estimated_time -%}
| Est. Time | {{ estimated_time }} |
{% endif -%}
{% if steps_count -%}
| Steps | {{ steps_count }} |
{% endif -%}
{% if code_blocks -%}
| Code Blocks | {{ code_blocks }} |
{% endif -%}
{% endif -%}

> {{ summary }}

{% if prerequisites -%}
## Prerequisites

{% for prereq in prerequisites -%}
- {{ prereq }}
{% endfor %}
{% endif -%}

{% if warnings -%}
## Warnings

{% for warning in warnings -%}
> ⚠️ {{ warning }}
{% endfor %}
{% endif -%}

{% if steps -%}
## Steps

{% for step in steps -%}
### Step {{ step.number }}: {{ step.title }}
{% if step.has_warning %}⚠️ {% endif %}{% if step.has_code %}💻 {% endif %}

{{ step.content }}

{% endfor %}
{% endif -%}

## Full Content

{{ content }}

## Source
[Original Tutorial]({{ source_url }})

## Related
{{ backlinks }}
"""

THREED_MODEL_TEMPLATE = """---
title: "{{ title }}"
source: "{{ source_url }}"
platform: "{{ platform }}"
creator: "{{ creator }}"
{% if download_count -%}
downloads: {{ download_count }}
{% endif -%}
{% if like_count -%}
likes: {{ like_count }}
{% endif -%}
{% if file_types -%}
file_types: {{ file_types }}
{% endif -%}
captured: {{ date_captured }}
tags: {{ tags }}
type: printable
{% if license -%}
license: "{{ license }}"
{% endif -%}
---

# {{ title }}

> {{ summary }}

## Model Info

| Field | Value |
|-------|-------|
| Platform | **{{ platform }}** |
| Creator | [{{ creator }}]({{ creator_url }}) |
{% if download_count -%}
| Downloads | {{ download_count }} |
{% endif -%}
{% if like_count -%}
| Likes | {{ like_count }} |
{% endif -%}
{% if file_types -%}
| File Types | {{ file_types_formatted }} |
{% endif -%}
{% if license -%}
| License | {{ license }} |
{% endif -%}

[View on {{ platform }}]({{ source_url }})

{% if images -%}
## Preview

{% for img in images -%}
![{{ title }}]({{ img }})
{% endfor -%}
{% endif -%}

{% if print_settings_formatted -%}
## Print Settings

{{ print_settings_formatted }}
{% endif -%}

{% if model_tags -%}
## Categories

{% for tag in model_tags -%}
`{{ tag }}` {% endfor %}
{% endif -%}

{% if description -%}
## Description

{{ description }}
{% endif -%}

## Related
{{ backlinks }}
"""

TEMPLATES: dict[ContentType, str] = {
    ContentType.ARTICLE: ARTICLE_TEMPLATE,
    ContentType.VIDEO: YOUTUBE_TEMPLATE,
    ContentType.REPO: GITHUB_TEMPLATE,
    ContentType.NEWS: NEWS_TEMPLATE,
    ContentType.WALKTHROUGH: WALKTHROUGH_TEMPLATE,
    ContentType.PRINTABLE: THREED_MODEL_TEMPLATE,
}


def get_template(content_type: ContentType) -> str:
    """
    Get the template for a content type.

    Args:
        content_type: The type of content to get the template for

    Returns:
        The Jinja2 template string for the specified content type.
        Defaults to ARTICLE_TEMPLATE if the content type is not found.

    Examples:
        >>> get_template(ContentType.ARTICLE)
        '---\\ntitle: "{{ title }}"\\n...'
        >>> get_template(ContentType.VIDEO)
        '---\\ntitle: "{{ title }}"\\n...'
    """
    return TEMPLATES.get(content_type, ARTICLE_TEMPLATE)

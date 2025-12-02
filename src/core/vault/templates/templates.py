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
captured: {{ date_captured }}
tags: {{ tags }}
type: repo
---

# {{ title }}

> {{ summary }}

## Repository Details
- **Owner:** {{ owner }}
- **Repository:** {{ repo_name }}
- **URL:** [View on GitHub]({{ source_url }})

## README Summary
{{ readme_summary }}

## Related
{{ backlinks }}
"""

NEWS_TEMPLATE = """---
title: "{{ title }}"
source: "{{ source_url }}"
source_name: "{{ source_name }}"
captured: {{ date_captured }}
tags: {{ tags }}
type: news
---

# {{ title }}

> {{ summary }}

## Source
**{{ source_name }}** - [Read Original]({{ source_url }})

## Content
{{ content }}

## Related
{{ backlinks }}
"""

WALKTHROUGH_TEMPLATE = """---
title: "{{ title }}"
source: "{{ source_url }}"
captured: {{ date_captured }}
tags: {{ tags }}
type: walkthrough
---

# {{ title }}

> {{ summary }}

## Source
[Original Walkthrough]({{ source_url }})

## Steps
{{ steps }}

## Related
{{ backlinks }}
"""

THREED_MODEL_TEMPLATE = """---
title: "{{ title }}"
source: "{{ source_url }}"
captured: {{ date_captured }}
tags: {{ tags }}
type: printable
---

# {{ title }}

> {{ summary }}

## Source
[View Model]({{ source_url }})

## Print Settings
{{ print_settings }}

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

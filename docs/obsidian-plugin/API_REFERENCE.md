# Claudsidian API Reference

Complete API documentation for integrating with the Claudsidian capture server.

## Server Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Base URL | `http://127.0.0.1:8765` | Local server address |
| mDNS Service | `_claudsidian._tcp.local.` | Service discovery |
| CORS | Open (`*`) | Allows browser extension/plugin access |

---

## Core Endpoints

### GET /

Returns API information and server status.

**Response:**
```json
{
  "name": "Claudsidian",
  "version": "0.1.0",
  "description": "AI-powered knowledge capture for Obsidian",
  "status": "running"
}
```

---

### GET /health

Simple health check.

**Response:**
```json
{
  "status": "healthy"
}
```

---

### GET /status

Returns detailed server configuration and API availability.

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "vault_path": "/path/to/vault",
  "apis": {
    "claude": true,
    "openrouter": true
  }
}
```

**Status Values:**
- `ok` - Fully configured and operational
- `degraded` - Missing some optional settings
- `error` - Critical configuration issues

---

## Capture Endpoint

### POST /capture

Captures a URL and creates a markdown note in the Obsidian vault.

**Request Body:**
```json
{
  "url": "https://example.com/article",
  "source": "browser",
  "force_type": null
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | Valid HTTP/HTTPS URL |
| `source` | enum | No | Capture source (default: `browser`) |
| `force_type` | enum | No | Override content type detection |

**Source Values:**
- `browser` - Browser extension
- `cli` - Command line interface
- `inbox` - Inbox processing
- `android` - Android share target

**Force Type Values:**
- `article` - Blog posts, essays, documentation
- `video` - YouTube, Vimeo, video content
- `repo` - GitHub repositories
- `news` - News articles
- `walkthrough` - Tutorials, how-to guides
- `printable` - 3D models (Thingiverse, Printables, Cults3D)

**Success Response (HTTP 200):**
```json
{
  "success": true,
  "note_path": "Learning/article-title.md",
  "title": "Article Title",
  "tags": ["technology", "ai", "knowledge-management"],
  "content_type": "article"
}
```

**Queued Response (HTTP 202):**
```json
{
  "queued": true,
  "queue_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Capture queued for processing"
}
```

**Duplicate Response (HTTP 409):**
```json
{
  "duplicate": true,
  "existing_note": "Learning/existing-article.md",
  "message": "Note already exists for this URL"
}
```

**Error Response (HTTP 400/500):**
```json
{
  "error": true,
  "message": "Error description",
  "code": "ERROR_CODE"
}
```

**Error Codes:**
| Code | Description |
|------|-------------|
| `INVALID_URL_SCHEME` | URL must use HTTP/HTTPS |
| `INVALID_SOURCE` | Invalid source value |
| `INVALID_FORCE_TYPE` | Invalid content type |
| `NOT_CONFIGURED` | Server not initialized |
| `CONFIG_ERROR` | Configuration loading failed |
| `CAPTURE_FAILED` | Capture processing failed |

---

## Queue Endpoints

### GET /queue

List all items in the capture queue.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | enum | Filter by status (optional) |

**Status Filter Values:**
- `pending` - Awaiting processing
- `processing` - Currently being processed
- `completed` - Successfully processed
- `failed` - Processing failed

**Response:**
```json
{
  "total": 5,
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "url": "https://example.com/article",
      "status": "pending",
      "attempts": 0,
      "error": null,
      "created_at": "2025-12-01T12:00:00+00:00",
      "updated_at": "2025-12-01T12:00:00+00:00"
    }
  ]
}
```

---

### GET /queue/{item_id}

Get a specific queue item by ID.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `item_id` | UUID | Queue item identifier |

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://example.com/article",
  "status": "pending",
  "attempts": 0,
  "error": null,
  "created_at": "2025-12-01T12:00:00+00:00",
  "updated_at": "2025-12-01T12:00:00+00:00"
}
```

---

### DELETE /queue/{item_id}

Remove an item from the queue.

**Response:**
```json
{
  "message": "Removed item 550e8400-e29b-41d4-a716-446655440000",
  "removed": true
}
```

---

### POST /queue/retry

Retry all failed items (resets status to `pending`).

**Response:**
```json
{
  "message": "Reset 3 items to pending",
  "count": 3
}
```

---

### POST /queue/retry/{item_id}

Retry a specific failed item.

**Response:**
```json
{
  "message": "Reset item 550e8400-e29b-41d4-a716-446655440000 to pending",
  "count": 1
}
```

---

### DELETE /queue

Clear items from queue by status.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | enum | `completed` | Items to clear |

**Status Values:**
- `completed` - Clear only completed items
- `failed` - Clear only failed items
- `all` - Clear all items

**Response:**
```json
{
  "message": "Cleared 5 items",
  "removed": true
}
```

---

## Queue Item Model

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "request": {
    "url": "https://example.com/article",
    "source": "browser",
    "timestamp": "2025-12-01T12:00:00Z",
    "force_type": null
  },
  "status": "pending",
  "attempts": 0,
  "error": null,
  "created_at": "2025-12-01T12:00:00Z",
  "updated_at": "2025-12-01T12:00:00Z"
}
```

---

## Service Discovery (mDNS)

The server advertises itself via mDNS for automatic discovery.

**Service Type:** `_claudsidian._tcp.local.`

**Properties:**
```json
{
  "version": "0.1.0",
  "api": "/capture",
  "path": "/"
}
```

**Example Discovery Response:**
```json
{
  "name": "Claudsidian Capture Server._claudsidian._tcp.local.",
  "host": "192.168.1.100",
  "port": 8765
}
```

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Successful operation |
| 202 | Capture queued for async processing |
| 400 | Invalid input |
| 404 | Resource not found |
| 409 | Duplicate URL (already captured) |
| 500 | Server error |

---

## TypeScript Types

```typescript
// Capture request
interface CaptureRequest {
  url: string;
  source?: 'browser' | 'cli' | 'inbox' | 'android';
  force_type?: 'article' | 'video' | 'repo' | 'news' | 'walkthrough' | 'printable';
}

// Capture response
interface CaptureResponse {
  success?: boolean;
  note_path?: string;
  title?: string;
  tags?: string[];
  content_type?: string;
  queued?: boolean;
  queue_id?: string;
  duplicate?: boolean;
  existing_note?: string;
  error?: boolean;
  message?: string;
  code?: string;
}

// Queue item
interface QueueItem {
  id: string;
  url: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  attempts: number;
  error: string | null;
  created_at: string;
  updated_at: string;
}

// Server status
interface ServerStatus {
  status: 'ok' | 'degraded' | 'error';
  version: string;
  vault_path: string;
  apis: {
    claude: boolean;
    openrouter: boolean;
  };
}
```

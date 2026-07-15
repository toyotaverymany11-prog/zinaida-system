# Grok Image-to-Video Workflow

This reference provides detailed instructions for using xAI Grok Imagine via Hermes Web UI to animate images into videos.

## Overview

Grok Image-to-Video is a prompt-driven video generation approach that animates static images with cinematic motion effects. It's ideal for quick video generation when you have an image and want to add motion without building a full composition.

## Prerequisites

- Hermes Web UI running with xAI integration configured
- xAI credentials (API key or OAuth completed)
- Local image file (PNG, JPEG, or WebP)
- Hermes Web UI bearer token

## Setup

### Token Resolution

The endpoint requires a Hermes Web UI bearer token. Resolve it in this order:

1. `AUTH_TOKEN` environment variable
2. `${HERMES_WEB_UI_HOME}/.token`
3. `${HERMES_WEBUI_STATE_DIR}/.token`
4. `~/.hermes-web-ui/.token`

### Base URL Resolution

Resolve the Hermes Web UI base URL in this order:

1. `HERMES_WEB_UI_URL` environment variable
2. `http://127.0.0.1:${PORT}` if `PORT` is set
3. `http://127.0.0.1:8648` for local development
4. `http://127.0.0.1:6060` when running from Docker Compose

## API Endpoint

```
POST <Hermes Web UI base URL>/api/hermes/media/grok-image-to-video
```

## Authentication

The endpoint is protected by Hermes Web UI auth. Send the Hermes Web UI server bearer token:

```bash
-H "Authorization: Bearer <token>"
```

## Profile Selection

Include the current Hermes profile header if specified in run instructions:

```bash
-H "X-Hermes-Profile: <profile-name>"
```

## Request Format

### Required Fields

- `image_path`: Absolute path to input image (PNG, JPEG, WebP)
- `prompt`: Motion and style instructions for the generated video

### Optional Fields

- `duration`: Video duration in seconds (1-15, defaults to 8)
- `output_path`: Absolute path for output MP4 (server saves to media directory if omitted)
- `timeout_ms`: Maximum wait time in milliseconds (defaults to 600000)

## Example Request

```bash
#!/usr/bin/env bash
set -euo pipefail

# Resolve token
TOKEN="${AUTH_TOKEN:-}"
if [ -z "$TOKEN" ] && [ -n "${HERMES_WEB_UI_HOME:-}" ] && [ -f "$HERMES_WEB_UI_HOME/.token" ]; then
  TOKEN="$(cat "$HERMES_WEB_UI_HOME/.token")"
fi
if [ -z "$TOKEN" ] && [ -n "${HERMES_WEBUI_STATE_DIR:-}" ] && [ -f "$HERMES_WEBUI_STATE_DIR/.token" ]; then
  TOKEN="$(cat "$HERMES_WEBUI_STATE_DIR/.token")"
fi
if [ -z "$TOKEN" ] && [ -f "$HOME/.hermes-web-ui/.token" ]; then
  TOKEN="$(cat "$HOME/.hermes-web-ui/.token")"
fi

if [ -z "$TOKEN" ]; then
  echo "Missing Hermes Web UI token. Check AUTH_TOKEN, HERMES_WEB_UI_HOME, HERMES_WEBUI_STATE_DIR, or ~/.hermes-web-ui/.token." >&2
  exit 1
fi

# Resolve base URL
BASE_URL="${HERMES_WEB_UI_URL:-}"
if [ -z "$BASE_URL" ]; then
  BASE_URL="http://127.0.0.1:${PORT:-8648}"
fi
BASE_URL="${BASE_URL%/}"

# Make request
curl -sS -X POST "$BASE_URL/api/hermes/media/grok-image-to-video" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "image_path": "/absolute/path/to/input.png",
    "prompt": "Animate the subject with a slow cinematic push-in and subtle natural motion.",
    "duration": 8,
    "output_path": "/absolute/path/to/output.mp4"
  }'
```

## Response Handling

### Success

Returns the generated MP4 file path.

### Error Responses

- `401`/`403`: Authentication failure - verify token and Hermes Web UI is running
- `missing_xai_token`: Set `XAI_API_KEY` or complete xAI OAuth in Hermes Web UI
- Connection failures: Verify Hermes Web UI is accessible at the resolved URL

## Troubleshooting

### Common Issues

1. **Missing xAI Token**:
   - Error: `missing_xai_token`
   - Solution: Set `XAI_API_KEY` environment variable or complete xAI OAuth in Hermes Web UI

2. **Authentication Errors (401/403)**:
   - Verify Hermes Web UI token is valid
   - Check that Hermes Web UI is running and accessible
   - Ensure token is from the correct source (Hermes Web UI media endpoint token, not login token)

3. **Connection Failures**:
   - Verify Hermes Web UI base URL is correct
   - Check that Hermes Web UI is running on the expected port
   - Test connectivity with a simple curl request to the endpoint

4. **Timeout Errors**:
   - Increase `timeout_ms` parameter if video generation takes longer than expected
   - Check xAI API rate limits and quotas

## Best Practices

### Prompt Engineering

- Be specific about motion type: "cinematic push-in", "subtle parallax", "camera orbit"
- Specify duration and style: "8 seconds, cinematic, warm color grading"
- Include subject details: "portrait of a person, natural lighting"

### Output Management

- Always specify absolute paths for both input and output
- Use descriptive output filenames: `output.mp4` → `product-demo-2024.mp4`
- Store outputs in organized directories by project

### Validation

Before using the generated video:
- Verify duration matches request
- Check visual quality and motion smoothness
- Ensure output file is accessible and not corrupted

## Use Cases

- Quick social media clips from product images
- Cinematic motion effects for presentations
- Animated thumbnails and previews
- Promotional video snippets from existing imagery

## Alternatives

If Grok Image-to-Video is unavailable or unsuitable:
- Use **HyperFrames** for HTML/CSS/JS-based motion graphics
- Use **Remotion** for React-based video projects with more control
- Use **manual editing** for precise frame-by-frame adjustments

## References

- Hermes Web UI Media Endpoints Documentation
- xAI Grok Imagine API Documentation
- Video Style Guide: `references/video-style-guide.md`
- Troubleshooting Guide: `references/troubleshooting.md`
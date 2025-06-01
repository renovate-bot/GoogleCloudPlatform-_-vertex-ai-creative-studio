# MCP Servers for Genmedia: Go Implementations

This directory houses the Go language implementations of Model Context Protocol (MCP) servers designed to interface with Google Cloud's generative media APIs. Each subdirectory contains a standalone MCP server that can be built and run independently.

These servers enable MCP clients (such as AI agents or other applications) to leverage powerful media generation and manipulation capabilities.

## Available Go MCP Servers:

*   **`mcp-avtool-go`**:
    *   Provides audio/video compositing and manipulation tools by instrumenting `ffmpeg` and `ffprobe`.
    *   Capabilities include media info retrieval, format conversion (e.g., WAV to MP3), GIF creation, combining audio/video, overlaying images, concatenating files, volume adjustment, and audio layering.
    *   Supports local file paths and GCS URIs for inputs/outputs.

*   **`mcp-chirp3-go`**:
    *   Offers Text-to-Speech (TTS) synthesis using Google Cloud TTS with Chirp3-HD voices.
    *   Tools: `chirp_tts` for synthesis (with custom pronunciation support) and `list_chirp_voices` for discovering available voices.
    *   Audio can be returned as base64 data or saved to a local directory.

*   **`mcp-imagen-go`**:
    *   Enables image generation using Google's Imagen models via Vertex AI.
    *   Tool: `imagen_t2i` for text-to-image generation.
    *   Supports various parameters like aspect ratio and number of images. Output can be directed to GCS, saved locally (including download from GCS if API saves there), or returned as base64 data.

*   **`mcp-lyria-go`**:
    *   Facilitates music generation using Google's Lyria models via Vertex AI.
    *   Tool: `lyria_generate_music` for creating music from text prompts.
    *   Supports parameters like negative prompts and seed. Output can be directed to GCS, saved locally, or returned as base64 data.

*   **`mcp-veo-go`**:
    *   Provides video generation capabilities using Google's Veo models via Vertex AI.
    *   Tools: `veo_t2v` (text-to-video) and `veo_i2v` (image-to-video).
    *   Supports parameters like aspect ratio and duration. Videos are saved to GCS by the API and can optionally be downloaded to a local directory.

## Common Features:

*   **Transport Protocols**: Most servers support `stdio` (default), `http` (streamable HTTP with CORS), and `sse` (Server-Sent Events) transports.
*   **Configuration**: Primarily through environment variables (e.g., `PROJECT_ID`, `LOCATION`, `PORT`, `GENMEDIA_BUCKET`).
*   **Google Cloud Authentication**: Relies on Application Default Credentials (ADC) or service account keys.

Please refer to the `README.md` file within each server's subdirectory for detailed information on its specific tools, parameters, environment variables, and usage examples.

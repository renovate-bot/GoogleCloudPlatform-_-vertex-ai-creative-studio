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

## Developing MCP Servers for Genmedia

This section provides guidance on how to understand the architecture and extend or create a new MCP server for Genmedia.

### Architecture

The MCP servers in this repository are all structured in a similar way. They all use the `mcp-common` package for configuration, file handling, and OpenTelemetry. They all use the `mcp-go` library to create the MCP server and tools. They all support the same transport protocols (`stdio`, `http`, and `sse`).

The `mcp-common` package provides the following functionality:

*   **Configuration**: The `config.go` file provides a way to load configuration from environment variables.
*   **File Utilities**: The `file_utils.go` file provides utility functions for working with files.
*   **GCS Utilities**: The `gcs_utils.go` file provides utility functions for working with Google Cloud Storage.
*   **OpenTelemetry**: The `otel.go` file provides a function for initializing OpenTelemetry.

### Extending an Existing Server

To extend an existing server, you'll need to do the following:

1.  Add a new tool to the server. You can do this by calling the `AddTool` method on the `server.MCPServer` struct.
2.  Implement the tool's handler function. The handler function will be called when the tool is invoked. The handler function should take a `context.Context` and a `mcp.CallToolRequest` as input and should return a `mcp.CallToolResult` and an error.

### Creating a New Server

To create a new server, you'll need to do the following:

1.  Create a new directory for the server.
2.  Create a new `go.mod` file for the server.
3.  Create a new `main.go` file for the server.
4.  In the `main.go` file, you'll need to do the following:
    1.  Create a new `server.MCPServer` struct.
    2.  Add one or more tools to the server.
    3.  Start the server.

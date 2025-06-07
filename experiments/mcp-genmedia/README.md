# MCP Servers for Google Cloud Genmedia APIs

This repository contains Model Context Protocol (MCP) servers that enable MCP clients (like AI agents) to access Google Cloud's generative media APIs.

*Generative Media*

*   **Imagen 3** - for image generation and editing
*   **Veo 2** - for video creation
*   **Chirp 3 HD** - for audio synthesis
*   **Lyria** - for music generation

*Compositing*

*   **AVTool** - for audio/video compositing and manipulation

Each server can be enabled and run separately, allowing flexibility for environments that don't require all capabilities.

## Installation

To install the MCP Servers for Genmedia, you will need [Go](https://go.dev/doc/install) installed on your system.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio.git
    cd vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go
    ```

2.  **Install the MCP Servers:**
    Each MCP server must be installed individually. From the `mcp-genmedia-go` directory, run the following commands to install the servers you need:

    ```bash
    # Install all servers
    go install ./...

    # Or, install a specific server (e.g., Imagen)
    go install ./mcp-imagen-go
    ```

3.  **Verify your installation:**
    Ensure the Go binaries are in your system's `PATH`.
    ```bash
    export PATH=$(go env GOPATH)/bin:$PATH
    ```
    You can then verify the installation by running the server with the `--help` flag:
    ```bash
    mcp-imagen-go --help
    ```

## Running the Servers

The MCP servers can be run using different transport protocols. The default is `stdio`.

To start a server in Streamable HTTP mode, use the `--transport http` flag:
```bash
mcp-imagen-go --transport http
```

## Configuration

The servers are configured primarily through environment variables. Key variables include:

*   `PROJECT_ID`: Your Google Cloud project ID.
*   `LOCATION`: The Google Cloud region for the APIs (e.g., `us-central1`).
*   `PORT`: The port for the HTTP server (e.g., `8080`).
*   `GENMEDIA_BUCKET`: The Google Cloud Storage bucket for media assets.

## Available Tools

Here is a high-level overview of the tools provided by each MCP server.

### Imagen

*   `imagen_t2i`: Generates an image from a text prompt.

### Veo

*   `veo_t2v`: Generates a video from a text prompt.
*   `veo_i2v`: Generates a video from a reference image and an optional prompt.

### Chirp 3 HD Voices

*   `chirp_tts`: Synthesizes audio from text.
*   `list_chirp_voices`: Lists available Chirp voices.

### Lyria

*   `lyria_generate_music`: Generates music from a text prompt.

### AVTool (Audio/Video Compositing)

*   `ffmpeg_get_media_info`: Retrieves media file information.
*   `ffmpeg_combine_audio_and_video`: Combines video and audio files.
*   `ffmpeg_concatenate_media_files`: Concatenates multiple media files.
*   `ffmpeg_video_to_gif`: Converts a video to a GIF.
*   `ffmpeg_convert_audio_wav_to_mp3`: Converts WAV audio to MP3.
*   `ffmpeg_overlay_image_on_video`: Overlays an image on a video.
*   `ffmpeg_adjust_volume`: Adjusts the volume of an audio file.
*   `ffmpeg_layer_audio_files`: Mixes multiple audio files.

## Authentication

The servers use Google's Application Default Credentials (ADC). Ensure you have authenticated by one of the following methods:

1.  Set up ADC: `gcloud auth application-default login`
2.  Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of your service account key file.

You may also need to grant your user or service account access to the Google Cloud Storage bucket:
```bash
gcloud storage buckets add-iam-policy-binding gs://BUCKET_NAME \
  --member=user:user@email.com \
  --role=roles/storage.objectUser
```

## Client Configurations

The MCP servers can be used with various clients and hosts. A sample MCP configuration JSON can be found at [genmedia-config.json](./sample-agents/mcp-inspector/genmedia-config.json).

This repository provides AI application samples for:

*   [Google ADK (Agent Development Kit)](./sample-agents/adk/README.md)
*   [Google Firebase Genkit](./sample-agents/genkit/README.md)

## Development and Contribution

For those interested in extending the existing servers or creating new ones, the `mcp-genmedia-go` directory contains a more detailed `README.md` with information on the architecture and development process. Please refer to the [mcp-genmedia-go/README.md](./mcp-genmedia-go/README.md) for more information.

## License

Apache 2.0

## Disclaimer

This is not an officially supported Google product.
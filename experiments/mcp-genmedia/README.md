# MCP Servers for Google Cloud Genmedia APIs

This repository contains Model Context Protocol (MCP) servers that enable MCP clients (like AI agents) to access Google Cloud's generative media APIs.

* Imagen 3 - for image generation and editing
* Veo 2 - for video creation
* Chirp 3 HD - for audio synthesis
* Lyria - for music generation

Additionally, there's a compositing MCP server, avtool, which instruments ffmpeg, to combine these together.

Each server can be enabled and run separately, allowing flexibility for environments that don't require all capabilities.

### Install the Vertex AI Genmedia MCP Servers

Install the MCP Servers for Genmedia locally.

You will need [Go](https://go.dev/doc/install) to install the Go versions of the MCP Servers for Genmedia.

The MCP Servers for Genmedia available in the /experimental/mcp-genmedia/mcp-genmedia-go directory can be installed with the following commands:

```bash
# step 1: clone the repo
git clone https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio.git
```

```bash
# Step 2: change directory to the mcp-genmedia-go directory
cd vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go
```

Please install the MCP server of your choice individually

```bash
# Step 3 (imagen example): install a single MCP Server for Genmedia
cd mcp-imagen-go/
go install .
```

### Verify your installation

Confirm that the go binaries are on your path

```bash
export PATH=$(go env GOPATH)/bin:$PATH
```

Test with `--help`

```bash
# imagen mcp
mcp-imagen-go --help
```


## Genmedia MCP Tools docs

Each of the servers can be used in STDIO and Streamable HTTP mode (with SSE mode still available). The default is STDIO.

To start a server in Streamable HTTP mode, use the `--transport http` flag.

### Imagen

The MCP Server for Imagen provides tools for image generation:

* `imagen_t2i`: Generates an image from a text prompt. Supports output to GCS, local disk, or as base64 data. (Follows the [Imagen API](https://cloud.google.com/vertex-ai/generative-ai/docs/image/overview))

### Veo

The MCP Server for Veo offers tools for video generation:

* `veo_t2v`: Generates a video from a provided text prompt.
* `veo_i2v`: Generates a video from a provided reference image (GCS URI) and an optional text prompt.
(Both tools save video to GCS and can optionally download it locally.)

### Chirp 3 HD Voices

The MCP Server for Chirp 3 HD Voices includes tools for speech synthesis:

* `chirp_tts`: Synthesizes audio from text using a specified Chirp 3 HD Voice. Can return audio data directly or save to a local file.
* `list_chirp_voices`: Lists available Chirp 3 HD voices, filterable by language.

### Lyria

The MCP Server for Lyria enables music generation:

* `lyria_generate_music`: Generates music from a text prompt. Supports output to GCS, local disk, or as base64 data.

### AVTool (Audio/Video Compositing)

The MCP Server for AVTool provides various media processing capabilities by instrumenting FFMpeg and FFprobe:

* `ffmpeg_get_media_info`: Retrieves detailed media information (metadata, streams).
* `ffmpeg_combine_audio_and_video`: Combines separate video and audio files.
* `ffmpeg_concatenate_media_files`: Concatenates multiple video or audio files.
* `ffmpeg_video_to_gif`: Converts a video segment to an animated GIF.
* `ffmpeg_convert_audio_wav_to_mp3`: Converts WAV audio to MP3.
* `ffmpeg_overlay_image_on_video`: Overlays an image onto a video.
* `ffmpeg_adjust_volume`: Adjusts the volume of an audio file.
* `ffmpeg_layer_audio_files`: Mixes multiple audio files together.
(Most AVTool tools support GCS URIs for input/output and local file operations.)

## Authentication

The server uses Google's authentication. Make sure you have either:

1. Set up Application Default Credentials (ADC)
2. Set a GOOGLE_APPLICATION_CREDENTIALS environment variable
3. Used `gcloud auth application-default login`


Please note, you may need to provide your user (user@email.com) with access to the Google Cloud Storage bucket (`BUCKET_NAME`).

```bash
gcloud storage buckets add-iam-policy-binding gs://BUCKET_NAME \
  --member=user:user@email.com \
  --role=roles/storage.objectUser
```

## Client Configurations

The MCP servers from this repo can be used various clients/hosts. 

A sample MCP configuration JSON can be seen at [genmedia-config.json](./sample-agents/mcp-inspector/genmedia-config.json).


This repository provides some AI application samples:

1. [Google ADK(Agent Development Kit)](https://google.github.io/adk-docs/) Agents (a prebuilt agent is provided, details [below](#using-the-prebuilt-google-adk-agent-as-client))
2. [Google Firebase Genkit](https://firebase.google.com/docs/genkit) with the [MCP plugin](https://github.com/firebase/genkit/tree/main/js/plugins/mcp)


### Using the Google ADK agent as client

Please refer to the [README file](./sample-agents/adk/README.md) for an example of locally running an ADK agent that uses the MCP Servers for Genmedia.

### Using Google Genkit agent as a client

Please refer to the [README file](./sample-agents/genkit/README.md) for locally running an example Genkit agent that uses the MCP Servers for Genmedia.


## License

Apache 2.0

## Disclaimer

This is not an officially supported Google product.

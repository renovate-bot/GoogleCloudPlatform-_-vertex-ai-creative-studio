# MCP Servers for Google Cloud Genmedia APIs

This repository contains Model Context Protocol (MCP) servers that enable MCP clients (like AI agents) to access Google Cloud's generative media APIs.

* Imagen 3 - for image generation and editing
* Veo 2 - for video creation
* Chirp 3 HD - for audio synthesis
* Lyria - for music generation

Each server can be enabled and run separately, allowing flexibility for environments that don't require all capabilities.

### Install the Vertex AI Genmedia MCP Servers

Install the MCP Servers for Genmedia locally.

You will need [Go](https://go.dev/doc/install) to install the Go versions of the MCP Servers for Genmedia.

The MCP Servers for Genmedia are in preview on a feature branch of the Genmedia Creative Studio project, [mcp-genmedia-servers](https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio/tree/mcp-genmedia-servers/experiments/mcp-genmedia).

```bash
# install the Chirp 3 HD Voices MCP Server
go install github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-chirp3-go@v0.1.0-alpha

# install the Imagen 3 MCP Server
go install github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-imagen-go@v0.1.0-alpha

# install the Veo 2 MCP Server
go install github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-veo-go@v0.1.0-alpha
```




## Genmedia MCP Tools docs

Each of the servers can be used in STDIO and SSE mode (Streamable HTTP coming soon). The default is STDIO.

To start a server in SSE mode, use the `--transport sse` flag.

### Imagen

The MCP Server for Imagen has the following tools:

* `imagen_t2i` - generate an image from a prompt, following the [Imagen API](https://cloud.google.com/vertex-ai/generative-ai/docs/image/overview) 

## Veo

The MCP Server for Veo has the following tools:

* `veo_t2v` - generate a video from a provided text prompt
* `veo_2v` - generate a video from a provided reference image and an optional text prompt

## Chirp 3 HD Voices

The MCP Server for Chirp 3 HD Voices has the following tools:

* `chirp_tts` - synthesize audio using a Chirp 3 HD Voice
* `list_chirp_voices` - list available voices for a particular language

## Authentication

The server uses Google's authentication. Make sure you have either:

1. Set up Application Default Credentials (ADC)
2. Set a GOOGLE_APPLICATION_CREDENTIALS environment variable
3. Used `gcloud auth application-default login`

## Client Configurations

The MCP servers from this repo can be used with the following clients

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
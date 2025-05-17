# ADK sample

Google Cloud Vertex AI Agent Development kit sample genmedia MCP tool use.

With a genmedia MCP server running ...


## Setup

Add an .env file to the `genmedia_agent` agent directory:

```bash
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="your-location" #e.g. us-central1
GOOGLE_GENAI_USE_VERTEXAI="True"
```

## Run the ADK debug UX

In this dir, start the adk web debug UX:

```bash
uv sync
source .venv/bin/activate
adk web
```

![adk web screenshot](./assets/adk-genmedia-mcp.png)]
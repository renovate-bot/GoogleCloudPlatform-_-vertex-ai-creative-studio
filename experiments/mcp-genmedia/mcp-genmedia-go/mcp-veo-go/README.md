# Veo MCP Server

This is the GenMedia Creative Studio Veo MCP server.


## Requirements

Environment variables `PROJECT_ID` and `LOCATION`

* `PROJECT_ID` - Google Cloud Project ID, eg. `gcloud config get project`
* `LOCATION` - region, optional, defaults to `us-central1`

## Run

The MCP Server can be used as either a STDIO or SSE server.

### STDIO 

To start a STDIO server, build this as a binary and install it

```bash
go install
```

This will install `mcp-veo-go` in your path, and you'll be able to call it as a binary.

### Server-Sent Events SSE

Start an MCP Server on :8080, with SSE endpoint at `/sse`

```bash
go run *.go --transport sse
```

## Examples

t2v

```json
{
    "aspect_ratio": "16:9",
    "bucket": "ghchinoy-genai-sa-assets/videos",
    "model": "veo-2.0-generate-001",
    "num_videos": 3,
    "prompt": "a cat running through the woods"
}
```

i2v

```json
{
    "aspect_ratio": "widescreen",
    "bucket": "ghchinoy-genai-sa-assets/videos",
    "image_uri": "gs://ghchinoy-genai-sa-assets/images/sheeps.png",
    "model": "veo-2.0-generate-001",
    "num_videos": 2,
    "prompt": ""
}
```
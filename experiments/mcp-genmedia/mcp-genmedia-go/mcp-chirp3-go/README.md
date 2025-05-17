# Veo MCP Server

This is the GenMedia Creative Studio Chirp 3 HD MCP server.


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

This will install `mcp-chirp3-go` in your path, and you'll be able to call it as a binary.

### Server-Sent Events SSE

Start an MCP Server on :8080, with SSE endpoint at `/sse`

```bash
go run *.go --transport sse
```

## Examples

list_chirp_voices: List voices

```json
{
  "method": "tools/call",
  "params": {
    "name": "list_chirp_voices",
    "arguments": {
      "language": "english (australia)"
    },
  }
}
```

chirp_tts: Synthesis

```json
{
  "method": "tools/call",
  "params": {
    "name": "chirp_tts",
    "arguments": {
      "output_filename_prefix": "chirp_audio",
      "text": "Synthesizes speech from text using Google Cloud TTS with Chirp3-HD voices and saves it as a local WAV file.",
      "voice_name": "en-AU-Chirp3-HD-Autonoe"
    },
  }
}
```
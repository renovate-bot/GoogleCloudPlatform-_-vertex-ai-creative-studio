# `mcp-gemini-go` MCP Server

This server provides an MCP interface to Google's Gemini models, allowing for multimodal content generation.

## Tools

### `gemini_image_generation`

Generates content (text and/or images) based on a multimodal prompt.

**Parameters:**

- `prompt` (string, required): The text prompt for content generation.
- `model` (string, optional): The specific Gemini model to use. Defaults to `gemini-1.5-pro-latest`.
- `images` (string array, optional): A list of local file paths or GCS URIs for input images.
- `output_directory` (string, optional): Local directory to save any generated image(s) to.
- `gcs_bucket_uri` (string, optional): GCS URI prefix to store any generated images.

**Example Usage:**

```bash
export PROJECT_ID=your-gcp-project

mcptools call gemini_generate_content --params '{"prompt": "a picture of a cat sitting on a table", "output_directory": "./output"}' ./mcp-gemini-go/mcp-gemini-go
```

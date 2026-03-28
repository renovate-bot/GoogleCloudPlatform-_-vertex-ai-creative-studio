# GenMedia MCP Servers for Antigravity

This directory contains the configuration files and agent skills necessary to use the Google GenMedia MCP Servers directly within [Antigravity](https://antigravity.google/docs/).

## 1. Configure MCP Servers

Antigravity manages custom MCP servers via a raw `mcp_config.json` file.

1. Open Antigravity.
2. Open the **MCP Store** panel via the "..." dropdown at the top of the editor's side panel.
3. Click on **Manage MCP Servers**.
4. Click on **View raw config**.
5. Copy the contents of the `mcp_config.json` file in this directory and paste it into the editor.
6. Replace `YOUR_GOOGLE_CLOUD_PROJECT_ID` and `YOUR_GOOGLE_CLOUD_STORAGE_BUCKET` with your actual GCP Project ID and GenMedia GCS bucket URI (e.g., `gs://my-cool-bucket`).

## 2. Install the Producer Skill

Antigravity features an incredibly powerful Agent Skills engine. We have packaged our expert "Producer" workflows (for complex audio assembly, Veo retry strategies, etc.) into a compatible skill format.

To install it, simply copy the `.agents` folder from this directory into the root of your current workspace:

```bash
cp -r sample-agents/antigravity/.agents /path/to/your/workspace/
```

Alternatively, to install it globally for all your Antigravity workspaces:

```bash
mkdir -p ~/.gemini/antigravity/skills
cp -r sample-agents/antigravity/.agents/skills/producer ~/.gemini/antigravity/skills/
```

Once installed, the Antigravity agent will automatically discover the skill. If you ask it to "create a podcast" or "generate a storyboard", it will seamlessly read the instructions and orchestrate the GenMedia tools like a pro!

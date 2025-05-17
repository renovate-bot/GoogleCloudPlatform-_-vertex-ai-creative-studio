# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
from contextlib import AsyncExitStack

from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    SseServerParams,
    StdioServerParameters,
)

load_dotenv()

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")


# ADK with MCP sample
async def create_agent():
    """Gets tools from MCP Server."""
    common_exit_stack = AsyncExitStack()
     
    # MCP Client (STDIO)
    # assumes you've installed the MCP server on your path
    veo, _ = await MCPToolset.from_server(
        connection_params=StdioServerParameters(
            command="mcp-veo-go", 
            env=dict(os.environ, PROJECT_ID=project_id),
        ),
        async_exit_stack=common_exit_stack,
    )

    # MCP Client (STDIO)
    # assumes you've installed the MCP server on your path
    chirp3, _ = await MCPToolset.from_server(
        connection_params=StdioServerParameters(
            command="mcp-chirp3-go",
            env=dict(os.environ, PROJECT_ID=project_id),
        ),
        async_exit_stack=common_exit_stack,
    )

    # MCP Client (SSE)
    # assumes you've started the MCP server separately
    # e.g. mcp-imagen-go --transport sse
    remote_imagen, _ = await MCPToolset.from_server(
        connection_params=SseServerParams(url="http://localhost:8080/sse"),
        async_exit_stack=common_exit_stack,
    )

    agent = LlmAgent(
        model="gemini-2.0-flash",
        name="genmedia_agent",
        instruction=(
            """You're a creative assistant that can help users with creating audio, images, and video via your generative media tools.
            Feel free to be helpful in your suggestions, based on the information you know or can retrieve from your tools.
            If you're asked to translate into other languages, please do.
            """
        ),
        tools=[
            *remote_imagen,
            *chirp3,
            *veo,
        ],
    )
    return agent, common_exit_stack


root_agent = create_agent()

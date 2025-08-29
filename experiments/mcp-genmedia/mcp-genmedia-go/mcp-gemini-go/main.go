// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"github.com/rs/cors"
	"google.golang.org/genai"
)

var (
	appConfig   *common.Config
	genAIClient *genai.Client
	transport   string
)

const (
	serviceName = "mcp-gemini-go"
	version     = "0.1.0"
)

func init() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	flag.StringVar(&transport, "t", "stdio", "Transport type (stdio, sse, or http)")
	flag.StringVar(&transport, "transport", "stdio", "Transport type (stdio, sse, or http)")
	flag.Parse()
}

func main() {
	appConfig = common.LoadConfig()

	// Override default location for Gemini models if not explicitly set
	if os.Getenv("LOCATION") == "" {
		log.Printf("LOCATION environment variable not set. Defaulting to 'global' for mcp-gemini-go.")
		appConfig.Location = "global"
	}

	tp, err := common.InitTracerProvider(serviceName, version)
	if err != nil {
		log.Fatalf("failed to initialize tracer provider: %v", err)
	}
	defer func() {
		if err := tp.Shutdown(context.Background()); err != nil {
			log.Printf("Error shutting down tracer provider: %v", err)
		}
	}()

	log.Printf("Initializing global GenAI client...")
	clientCtx, clientCancel := context.WithTimeout(context.Background(), 1*time.Minute)
	defer clientCancel()

	clientConfig := &genai.ClientConfig{
		Backend:  genai.BackendVertexAI,
		Project:  appConfig.ProjectID,
		Location: appConfig.Location,
	}
	if appConfig.ApiEndpoint != "" {
		log.Printf("Using custom Vertex AI endpoint: %s", appConfig.ApiEndpoint)
		clientConfig.HTTPOptions.BaseURL = appConfig.ApiEndpoint
	}

	genAIClient, err = genai.NewClient(clientCtx, clientConfig)
	if err != nil {
		log.Fatalf("Error creating global GenAI client: %v", err)
	}
	log.Printf("Global GenAI client initialized successfully.")

	s := server.NewMCPServer("Gemini", version)

	tool := mcp.NewTool("gemini_image_generation",
		mcp.WithDescription("Generates content (text and/or images) based on a multimodal prompt using Gemini 2.5 Flash Image generation. This model is also called nano-banana."),
		mcp.WithString("prompt", mcp.Required(), mcp.Description("The text prompt for content generation.")),
		mcp.WithString("model", mcp.DefaultString("gemini-2.5-flash-image-preview"), mcp.Description("The specific Gemini model to use.")),
		mcp.WithArray("images", mcp.Description("Optional. A list of local file paths or GCS URIs for input images.")),
		mcp.WithString("output_directory", mcp.Description("Optional. Local directory to save generated image(s) to.")),
		mcp.WithString("gcs_bucket_uri", mcp.Description("Optional. GCS URI prefix to store generated images (e.g., your-bucket/outputs/).")),
	)

	handlerWithClient := func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return geminiGenerateContentHandler(genAIClient, ctx, request)
	}
	s.AddTool(tool, handlerWithClient)

	log.Printf("Starting Gemini MCP Server (Version: %s, Transport: %s)", version, transport)

	if transport == "sse" {
		sseServer := server.NewSSEServer(s, server.WithBaseURL("http://localhost:8082"))
		log.Printf("Gemini MCP Server listening on SSE at :8082")
		if err := sseServer.Start(":8082"); err != nil {
			log.Fatalf("SSE Server error: %v", err)
		}
	} else if transport == "http" {
		mcpHTTPHandler := server.NewStreamableHTTPServer(s)
		c := cors.New(cors.Options{
			AllowedOrigins:   []string{"*"},
			AllowedMethods:   []string{http.MethodGet, http.MethodPost, http.MethodPut, http.MethodDelete, http.MethodOptions, http.MethodHead},
			AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token", "X-MCP-Progress-Token"},
			ExposedHeaders:   []string{"Link"},
			AllowCredentials: true,
			MaxAge:           300,
		})
		handlerWithCORS := c.Handler(mcpHTTPHandler)
		httpPort := os.Getenv("PORT")
		if httpPort == "" {
			httpPort = "8080"
		}
		listenAddr := fmt.Sprintf(":%s", httpPort)
		log.Printf("Gemini MCP Server listening on HTTP at %s/mcp", listenAddr)
		if err := http.ListenAndServe(listenAddr, handlerWithCORS); err != nil {
			log.Fatalf("HTTP Server error: %v", err)
		}
	} else {
		log.Printf("Gemini MCP Server listening on STDIO")
		if err := server.ServeStdio(s); err != nil {
			log.Fatalf("STDIO Server error: %v", err)
		}
	}
	log.Println("Gemini Server has stopped.")
}

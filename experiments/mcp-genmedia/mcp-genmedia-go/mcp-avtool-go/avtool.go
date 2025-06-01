package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"

	"github.com/mark3labs/mcp-go/server"
	"github.com/rs/cors"
)

// init handles command-line flags and initial logging setup.
func init() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	initConfigFlags() // From config.go - call to parse flags
}

// main is the entry point of the application.
func main() {
	// flag.Parse() should be called in main, after all flags are defined.
	// Since initConfigFlags calls flag.String, flag.Parse should be here.
	// However, the mcp-go server library might also define flags or expect parsing at a certain time.
	// For now, let's assume it's safe to parse here. If there are conflicts or order issues
	// with flags defined by the mcp-go library, this might need adjustment.
	// The original code had flag.Parse() in main before loadConfiguration.
	// Let's keep it that way for now.
	flag.Parse() // Ensure flags are parsed before use

	loadConfiguration() // From config.go

	s := server.NewMCPServer(
		"AV Compositing Tool", // More general name
		version, // From config.go
	)

	// Register tools - these functions are now in mcp_handlers.go
	addConvertAudioTool(s)
	addCombineAudioVideoTool(s)
	addOverlayImageOnVideoTool(s)
	addConcatenateMediaTool(s)
	addAdjustVolumeTool(s)
	addLayerAudioTool(s)
	addCreateGifTool(s)
	addGetMediaInfoTool(s)

	log.Printf("Starting AV Compositing Tool (avtool) MCP Server (Version: %s, Transport: %s)", version, transport) // version, transport from config.go

	if transport == "sse" {
		sseServer := server.NewSSEServer(s, server.WithBaseURL("http://localhost:8081"))
		log.Printf("AV Compositing Tool (avtool) MCP Server listening on SSE at :8081")
		if err := sseServer.Start(":8081"); err != nil {
			log.Fatalf("SSE Server error: %v", err)
		}
	} else if transport == "http" {
		mcpHTTPHandler := server.NewStreamableHTTPServer(s) // Base path /mcp

		c := cors.New(cors.Options{
			AllowedOrigins:   []string{"*"}, // Consider making this configurable
			AllowedMethods:   []string{http.MethodGet, http.MethodPost, http.MethodPut, http.MethodDelete, http.MethodOptions, http.MethodHead},
			AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token", "X-MCP-Progress-Token"},
			ExposedHeaders:   []string{"Link"},
			AllowCredentials: true,
			MaxAge:           300,
		})

		handlerWithCORS := c.Handler(mcpHTTPHandler)

		httpPort := getEnv("PORT", "8080") // From config.go
		listenAddr := fmt.Sprintf(":%s", httpPort)
		log.Printf("AV Compositing Tool (avtool) MCP Server listening on HTTP at %s/mcp and CORS enabled", listenAddr)
		if err := http.ListenAndServe(listenAddr, handlerWithCORS); err != nil {
			log.Fatalf("HTTP Server error: %v", err)
		}
	} else { // Default to stdio
		if transport != "stdio" && transport != "" {
			log.Printf("Unsupported transport type '%s' specified, defaulting to stdio.", transport)
		}
		log.Printf("AV Compositing Tool (avtool) MCP Server listening on STDIO")
		if err := server.ServeStdio(s); err != nil {
			log.Fatalf("STDIO Server error: %v", err)
		}
	}
	log.Println("AV Compositing Tool (avtool) Server has stopped.")
}

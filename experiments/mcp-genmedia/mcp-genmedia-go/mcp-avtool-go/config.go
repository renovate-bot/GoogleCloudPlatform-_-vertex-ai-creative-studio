package main

import (
	"flag"
	"log"
	"os"
)

var (
	// MCP Server settings
	transport string
	version   = "1.0.10" // Version increment for improvements to concat

	// Google Cloud settings - typically set via environment variables
	gcpProjectID      string // PROJECT_ID for GCS operations
	gcpLocation       string // LOCATION (not directly used by FFMpeg server but good for consistency)
	genmediaBucketEnv string // To store GENMEDIA_BUCKET env var
)

const (
	defaultTempDirPrefix = "mcp_avtool_"
)

// init handles command-line flags for transport.
// Note: log.SetFlags is typically called once, usually in the main init.
// If other files have init(), ensure flags are not redefined.
func initConfigFlags() { // Renamed to avoid conflict if main avtool.go also has init()
	flag.StringVar(&transport, "t", "stdio", "Transport type (stdio, sse, or http)")
	flag.StringVar(&transport, "transport", "stdio", "Transport type (stdio, sse, or http)")
}

// getEnv retrieves an environment variable by key. If the variable is not set
// or is empty, it logs a message and returns the fallback value.
func getEnv(key, fallback string) string {
	if value, exists := os.LookupEnv(key); exists && value != "" {
		return value
	}
	log.Printf("Environment variable %s not set or empty, using fallback: %s", key, fallback)
	return fallback
}

// loadConfiguration loads settings from environment variables.
func loadConfiguration() {
	gcpProjectID = os.Getenv("PROJECT_ID")
	if gcpProjectID == "" {
		log.Println("WARNING: PROJECT_ID environment variable not set. GCS operations will not be available.")
	} else {
		log.Printf("Using GCP Project ID: %s for GCS operations.", gcpProjectID)
	}
	gcpLocation = getEnv("LOCATION", "us-central1")
	log.Printf("Using GCP Location: %s (primarily for GCS client initialization context if needed).", gcpLocation)

	genmediaBucketEnv = getEnv("GENMEDIA_BUCKET", "") // Use existing getEnv helper, fallback to empty string
	if genmediaBucketEnv != "" {
		log.Printf("Default GCS output bucket configured from GENMEDIA_BUCKET: %s", genmediaBucketEnv)
	}
}

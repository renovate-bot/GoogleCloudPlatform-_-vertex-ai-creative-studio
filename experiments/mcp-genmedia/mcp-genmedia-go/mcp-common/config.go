package common

import (
	"log"
	"os"
)

type Config struct {
	ProjectID           string
	Location            string
	GenmediaBucket      string
	LyriaLocation       string
	LyriaModelPublisher string
	DefaultLyriaModelID string
}

func LoadConfig() *Config {
	projectID := os.Getenv("PROJECT_ID")
	if projectID == "" {
		log.Fatal("PROJECT_ID environment variable not set. Please set the env variable, e.g. export PROJECT_ID=$(gcloud config get project)")
	}

	return &Config{
		ProjectID:           projectID,
		Location:            GetEnv("LOCATION", "us-central1"),
		GenmediaBucket:      GetEnv("GENMEDIA_BUCKET", ""),
		LyriaLocation:       GetEnv("LYRIA_LOCATION", GetEnv("LOCATION", "us-central1")),
		LyriaModelPublisher: GetEnv("LYRIA_MODEL_PUBLISHER", "google"),
		DefaultLyriaModelID: GetEnv("DEFAULT_LYRIA_MODEL_ID", "lyria-002"),
	}
}

func GetEnv(key, fallback string) string {
	if value, exists := os.LookupEnv(key); exists && value != "" {
		return value
	}
	log.Printf("Environment variable %s not set or empty, using fallback: %s", key, fallback)
	return fallback
}

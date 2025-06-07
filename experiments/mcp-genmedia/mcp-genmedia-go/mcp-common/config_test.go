package common

import (
	"os"
	"testing"
)

func TestLoadConfig(t *testing.T) {
	t.Run("with all env vars set", func(t *testing.T) {
		os.Setenv("PROJECT_ID", "test-project")
		os.Setenv("LOCATION", "test-location")
		os.Setenv("GENMEDIA_BUCKET", "test-bucket")
		os.Setenv("LYRIA_LOCATION", "lyria-location")
		os.Setenv("LYRIA_MODEL_PUBLISHER", "lyria-publisher")
		os.Setenv("DEFAULT_LYRIA_MODEL_ID", "lyria-model")

		cfg := LoadConfig()

		if cfg.ProjectID != "test-project" {
			t.Errorf("expected ProjectID to be 'test-project', but got '%s'", cfg.ProjectID)
		}
		if cfg.Location != "test-location" {
			t.Errorf("expected Location to be 'test-location', but got '%s'", cfg.Location)
		}
		if cfg.GenmediaBucket != "test-bucket" {
			t.Errorf("expected GenmediaBucket to be 'test-bucket', but got '%s'", cfg.GenmediaBucket)
		}
		if cfg.LyriaLocation != "lyria-location" {
			t.Errorf("expected LyriaLocation to be 'lyria-location', but got '%s'", cfg.LyriaLocation)
		}
		if cfg.LyriaModelPublisher != "lyria-publisher" {
			t.Errorf("expected LyriaModelPublisher to be 'lyria-publisher', but got '%s'", cfg.LyriaModelPublisher)
		}
		if cfg.DefaultLyriaModelID != "lyria-model" {
			t.Errorf("expected DefaultLyriaModelID to be 'lyria-model', but got '%s'", cfg.DefaultLyriaModelID)
		}
	})

	t.Run("with some env vars missing", func(t *testing.T) {
		os.Unsetenv("LOCATION")
		os.Unsetenv("GENMEDIA_BUCKET")
		os.Unsetenv("LYRIA_LOCATION")
		os.Unsetenv("LYRIA_MODEL_PUBLISHER")
		os.Unsetenv("DEFAULT_LYRIA_MODEL_ID")

		cfg := LoadConfig()

		if cfg.Location != "us-central1" {
			t.Errorf("expected Location to be 'us-central1', but got '%s'", cfg.Location)
		}
		if cfg.GenmediaBucket != "" {
			t.Errorf("expected GenmediaBucket to be '', but got '%s'", cfg.GenmediaBucket)
		}
		if cfg.LyriaLocation != "us-central1" {
			t.Errorf("expected LyriaLocation to be 'us-central1', but got '%s'", cfg.LyriaLocation)
		}
		if cfg.LyriaModelPublisher != "google" {
			t.Errorf("expected LyriaModelPublisher to be 'google', but got '%s'", cfg.LyriaModelPublisher)
		}
		if cfg.DefaultLyriaModelID != "lyria-002" {
			t.Errorf("expected DefaultLyriaModelID to be 'lyria-002', but got '%s'", cfg.DefaultLyriaModelID)
		}
	})
}

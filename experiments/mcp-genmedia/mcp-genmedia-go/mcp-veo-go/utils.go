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
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"cloud.google.com/go/storage"
)

// getEnv retrieves an environment variable by key. If the variable is not set
// or is empty, it logs a message and returns the fallback value.
func getEnv(key, fallback string) string {
	if value, exists := os.LookupEnv(key); exists && value != "" {
		return value
	}
	log.Printf("Environment variable %s not set or empty, using fallback: %s", key, fallback)
	return fallback
}

// inferMimeTypeFromURI attempts to guess the MIME type from the file extension.
// Only "image/png" and "image/jpeg" are supported by the API.
func inferMimeTypeFromURI(uri string) string {
	ext := strings.ToLower(filepath.Ext(uri))
	switch ext {
	case ".png":
		return "image/png"
	case ".jpg", ".jpeg":
		return "image/jpeg"
	default:
		return ""
	}
}

// parseGCSPath splits a GCS URI (gs://bucket/object/path) into bucket and object path.
func parseGCSPath(gcsURI string) (bucketName string, objectName string, err error) {
	if !strings.HasPrefix(gcsURI, "gs://") {
		return "", "", fmt.Errorf("invalid GCS URI: must start with gs://")
	}
	trimmedURI := strings.TrimPrefix(gcsURI, "gs://")
	parts := strings.SplitN(trimmedURI, "/", 2)
	if len(parts) < 2 || parts[0] == "" || parts[1] == "" {
		return "", "", fmt.Errorf("invalid GCS URI format: %s. Expected gs://bucket/object", gcsURI)
	}
	return parts[0], parts[1], nil
}

// downloadFromGCS downloads an object from GCS to a local file.
// The parentCtx is the context from the handler, used for creating the storage client.
// A new derived context with timeout is used for the actual download operation.
func downloadFromGCS(parentCtx context.Context, gcsURI string, localDestPath string) error {
	bucketName, objectName, err := parseGCSPath(gcsURI)
	if err != nil {
		return fmt.Errorf("parseGCSPath for %s: %w", gcsURI, err)
	}

	// Use parentCtx for creating the storage client.
	// If parentCtx is already canceled, NewClient might fail or operations might fail quickly.
	storageClient, err := storage.NewClient(parentCtx)
	if err != nil {
		return fmt.Errorf("storage.NewClient: %w", err)
	}
	defer storageClient.Close()

	// Create a new context with its own timeout for the GCS download operation.
	// This makes the download itself resilient if parentCtx has a very short deadline.
	gcsDownloadCtx, cancel := context.WithTimeout(parentCtx, 2*time.Minute) // 2-minute timeout for each download
	defer cancel()

	rc, err := storageClient.Bucket(bucketName).Object(objectName).NewReader(gcsDownloadCtx)
	if err != nil {
		return fmt.Errorf("Object(%q in bucket %q).NewReader: %w", objectName, bucketName, err)
	}
	defer rc.Close()

	// Ensure destination directory exists before creating the file
	destDir := filepath.Dir(localDestPath)
	if err := os.MkdirAll(destDir, 0755); err != nil {
		return fmt.Errorf("os.MkdirAll for directory %s: %w", destDir, err)
	}

	f, err := os.Create(localDestPath)
	if err != nil {
		return fmt.Errorf("os.Create for %s: %w", localDestPath, err)
	}
	defer f.Close()

	if _, err := io.Copy(f, rc); err != nil {
		return fmt.Errorf("io.Copy to %s: %w", localDestPath, err)
	}

	log.Printf("Successfully downloaded GCS object %s to %s", gcsURI, localDestPath)
	return nil
}

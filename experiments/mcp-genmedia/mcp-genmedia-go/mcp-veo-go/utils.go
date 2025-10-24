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

// Package main implements an MCP server for Google's Veo models.

package main

import (
	"fmt"
	"log"
	"path/filepath"
	"strings"

	common "github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
)

// inferMimeTypeFromURI attempts to determine the MIME type of a file based on its extension.
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

// parseCommonVideoParams extracts and validates video generation parameters from the request arguments.
func parseCommonVideoParams(args map[string]interface{}, appConfig *common.Config) (string, string, string, string, int32, int32, bool, error) {
	// Model
	modelInput, ok := args["model"].(string)
	if !ok || modelInput == "" {
		modelInput = "veo-2.0-generate-001"
	}
	canonicalName, found := common.ResolveVeoModel(modelInput)
	if !found {
		return "", "", "", "", 0, 0, false, fmt.Errorf("model '%s' is not a valid or supported model name", modelInput)
	}
	model := canonicalName
	modelDetails := common.SupportedVeoModels[model]

	// GCS Bucket
	gcsBucket, _ := args["bucket"].(string)
	if gcsBucket != "" {
		gcsBucket = common.EnsureGCSPathPrefix(gcsBucket)
	} else if appConfig.GenmediaBucket != "" {
		gcsBucket = fmt.Sprintf("gs://%s/veo_outputs/", appConfig.GenmediaBucket)
		log.Printf("Handler: 'bucket' parameter not provided, using default constructed from GENMEDIA_BUCKET: %s", gcsBucket)
	}

	// Output Directory
	outputDir, _ := args["output_directory"].(string)

	// Number of Videos
	var numberOfVideos int32 = 1
	if numVideosArg, ok := args["num_videos"].(float64); ok {
		numberOfVideos = int32(numVideosArg)
	}
	if numberOfVideos < 1 {
		numberOfVideos = 1
	}
	if numberOfVideos > modelDetails.MaxVideos {
		log.Printf("Warning: Requested %d videos, but model %s only supports up to %d. Adjusting to max.", numberOfVideos, model, modelDetails.MaxVideos)
		numberOfVideos = modelDetails.MaxVideos
	}

	// Duration
	var durationSecs int32 = modelDetails.DefaultDuration
	if durationArg, ok := args["duration"].(float64); ok {
		durationSecs = int32(durationArg)
	}
	validDuration := false
	for _, d := range modelDetails.SupportedDurations {
		if d == durationSecs {
			validDuration = true
			break
		}
	}
	if !validDuration {
		// Create a string representation of the supported durations for the error message
		durationsStr := make([]string, len(modelDetails.SupportedDurations))
		for i, d := range modelDetails.SupportedDurations {
			durationsStr[i] = fmt.Sprintf("%d", d)
		}
		return "", "", "", "", 0, 0, false, fmt.Errorf("duration '%d' is not supported by model %s. Supported durations are: [%s]", durationSecs, model, strings.Join(durationsStr, ", "))
	}

	// Aspect Ratio
	finalAspectRatio, _ := args["aspect_ratio"].(string)
	if finalAspectRatio == "" {
		finalAspectRatio = "16:9"
	}
	validRatio := false
	for _, r := range modelDetails.SupportedAspectRatios {
		if r == finalAspectRatio {
			validRatio = true
			break
		}
	}
	if !validRatio {
		return "", "", "", "", 0, 0, false, fmt.Errorf("aspect ratio '%s' is not supported by model %s", finalAspectRatio, model)
	}

	// Generate Audio
	var generateAudio bool = true // Default to true as per user request
	if genAudioArg, ok := args["generate_audio"].(bool); ok {
		generateAudio = genAudioArg
	}

	if generateAudio && !modelDetails.SupportsGenerateAudio {
		return "", "", "", "", 0, 0, false, fmt.Errorf("generate_audio is set to true, but is not supported by model %s", model)
	}

	return gcsBucket, outputDir, model, finalAspectRatio, numberOfVideos, durationSecs, generateAudio, nil
}
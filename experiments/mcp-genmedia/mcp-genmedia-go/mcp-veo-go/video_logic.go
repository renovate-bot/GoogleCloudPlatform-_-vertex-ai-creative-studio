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
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"path/filepath"
	"strings"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"google.golang.org/genai"
)

// parseCommonVideoParams parses common video generation parameters from the request.
// gcsBucket is a named return value, so it's already declared in this function's scope.
func parseCommonVideoParams(params map[string]interface{}) (gcsBucket, outputDir, model, finalAspectRatio string, numberOfVideos int32, durationSeconds *int32, err error) {
	// Initialize default values for some parameters
	model = "veo-2.0-generate-001" // Default model
	numberOfVideos = 1             // Default number of videos
	finalAspectRatio = "16:9"      // Default aspect ratio
	defaultDurationVal := int32(5) // Default duration in seconds
	durationSeconds = &defaultDurationVal

	// Retrieve and process the 'bucket' parameter
	bucketParamValue, bucketParamProvided := params["bucket"].(string)
	trimmedBucketParam := strings.TrimSpace(bucketParamValue)

	if bucketParamProvided && trimmedBucketParam != "" {
		// User explicitly provided a non-empty bucket parameter.
		gcsBucket = trimmedBucketParam // Assign to the named return value gcsBucket
	} else if genmediaBucketEnv != "" {
		// User either did not provide the 'bucket' parameter, or provided an empty one,
		// AND the GENMEDIA_BUCKET environment variable is set.
		gcsBucket = fmt.Sprintf("gs://%s/veo_outputs/", genmediaBucketEnv) // Assign to gcsBucket
		if !bucketParamProvided {
			log.Printf("Handler veo: 'bucket' parameter (for OutputGCSURI) not provided, using default constructed from GENMEDIA_BUCKET: %s", gcsBucket)
		} else { // bucketParamProvided was true, but trimmedBucketParam was empty
			log.Printf("Handler veo: 'bucket' parameter (for OutputGCSURI) was provided but empty, using default constructed from GENMEDIA_BUCKET: %s", gcsBucket)
		}
	} else {
		// Parameter was not provided or was empty, AND GENMEDIA_BUCKET is not set.
		// This is an error condition as a bucket is required.
		err = errors.New("Google Cloud Storage bucket (parameter 'bucket') must be provided as a non-empty string, or the GENMEDIA_BUCKET environment variable must be set and non-empty")
		return // Return early as gcsBucket is invalid
	}

	// Ensure gcsBucket (whether from param or env) starts with gs://
	if !strings.HasPrefix(gcsBucket, "gs://") {
		gcsBucket = "gs://" + gcsBucket
		log.Printf("Bucket name/URI '%s' did not start with 'gs://', prepended. New bucket URI: %s", strings.TrimPrefix(gcsBucket, "gs://"), gcsBucket)
	}

	// Ensure gcsBucket ends with a slash for API compatibility (treated as a directory)
	if !strings.HasSuffix(gcsBucket, "/") {
		gcsBucket += "/"
		log.Printf("Appended '/' to bucket URI for directory structure. New URI: %s", gcsBucket)
	}

	// Process 'output_directory' parameter
	if dir, ok := params["output_directory"].(string); ok && strings.TrimSpace(dir) != "" {
		outputDir = strings.TrimSpace(dir)
	}

	// Process 'model' parameter
	if modelArg, ok := params["model"].(string); ok && modelArg != "" {
		model = modelArg
	} else {
		log.Printf("Model not provided or empty, using default: %s", model)
	}

	// Process 'num_videos' parameter
	if numVideosArg, ok := params["num_videos"]; ok {
		if numVideosFloat, okFloat := numVideosArg.(float64); okFloat {
			parsedNumVideos := int32(numVideosFloat)
			if parsedNumVideos >= 1 && parsedNumVideos <= 4 {
				numberOfVideos = parsedNumVideos
			} else {
				log.Printf("Warning: num_videos '%.0f' is outside the accepted range (1-4). Clamping to default/bounds.", numVideosFloat)
				if parsedNumVideos < 1 {
					numberOfVideos = 1
				} else {
					numberOfVideos = 4
				}
			}
		} else {
			log.Printf("Warning: num_videos was not a float64, received %T. Using default (%d).", numVideosArg, numberOfVideos)
		}
	}
	// Clamping already handled above, but ensure it's within 1-4 as a final check (though defaults should be fine)
	if numberOfVideos < 1 {
		numberOfVideos = 1
	}
	if numberOfVideos > 4 {
		numberOfVideos = 4
	}

	// Process 'aspect_ratio' parameter
	aspectRatioInput := finalAspectRatio // Default to "16:9"
	if aspectRatioArg, ok := params["aspect_ratio"].(string); ok && aspectRatioArg != "" {
		aspectRatioInput = strings.ToLower(strings.TrimSpace(aspectRatioArg))
	} else {
		log.Printf("Aspect ratio not provided or empty, using default: %s", finalAspectRatio)
	}

	switch aspectRatioInput {
	case "widescreen", "16:9":
		finalAspectRatio = "16:9"
	case "portrait", "9:16":
		finalAspectRatio = "9:16"
	default:
		if aspectRatioInput != "16:9" { // Only log if it was something unexpected
			log.Printf("Invalid aspect_ratio value '%s' received. Defaulting to '16:9'. Valid options are '16:9', '9:16', 'widescreen', or 'portrait'.", aspectRatioInput)
		}
		finalAspectRatio = "16:9" // Ensure default if invalid
	}

	// Process 'duration' parameter
	if durationArg, ok := params["duration"]; ok {
		if durationFloat, okFloat := durationArg.(float64); okFloat {
			parsedDuration := int32(durationFloat)
			if parsedDuration >= 5 && parsedDuration <= 8 {
				durationSeconds = &parsedDuration
			} else {
				log.Printf("Warning: duration '%.0f' is outside the accepted range (5-8 seconds). Using default (%d seconds).", durationFloat, *durationSeconds)
			}
		} else {
			log.Printf("Warning: duration was not a float64, received %T. Using default (%d seconds).", durationArg, *durationSeconds)
		}
	} else {
		log.Printf("Duration not provided, using default (%d seconds).", *durationSeconds)
	}
	return // Returns the named return values (gcsBucket, outputDir, model, finalAspectRatio, numberOfVideos, durationSeconds, err)
}

func callGenerateVideosAPI(
	client *genai.Client,
	parentCtx context.Context, // Renamed from ctx to avoid conflict with operationCtx
	mcpServer *server.MCPServer,
	progressToken mcp.ProgressToken,
	outputDir string,
	modelName string,
	prompt string,
	image *genai.Image,
	config *genai.GenerateVideosConfig,
	callType string,
) (*mcp.CallToolResult, error) {

	attemptLocalDownload := outputDir != ""

	// Context for the entire GenerateVideos operation, including polling.
	// We derive the operation context from the parent context to ensure that if the
	// client disconnects or the parent request is canceled, we propagate the
	// cancellation to the long-running GenAI operation.
	operationCtx, operationCancel := context.WithTimeout(parentCtx, 5*time.Minute) // Timeout for the entire GenAI operation + polling
	defer operationCancel()

	logMsg := fmt.Sprintf("Initiating GenerateVideos (%s) with Model: %s", callType, modelName)
	if image != nil && image.GCSURI != "" {
		logMsg += fmt.Sprintf(", ImageGCSURI: %s, ImageMIMEType: %s", image.GCSURI, image.MIMEType)
	}
	if prompt != "" {
		logMsg += fmt.Sprintf(", Prompt: \"%s\"", strings.ReplaceAll(prompt, "\n", " ")) // Sanitize prompt for logging
	}
	if config.DurationSeconds != nil {
		logMsg += fmt.Sprintf(", Duration: %ds", *config.DurationSeconds)
	}
	logMsg += fmt.Sprintf(", OutputGCS: %s. Operation timeout: %v", config.OutputGCSURI, 5*time.Minute)
	if attemptLocalDownload {
		logMsg += fmt.Sprintf(". Will attempt to download to local directory: '%s'", outputDir)
	}
	log.Print(logMsg)

	startTime := time.Now()

	// Use operationCtx for the initial call to GenerateVideos
	operation, err := client.Models.GenerateVideos(operationCtx, modelName, prompt, image, config)
	if err != nil {
		if errors.Is(err, context.DeadlineExceeded) && operationCtx.Err() == context.DeadlineExceeded {
			log.Printf("GenerateVideos (%s) failed: initial call timed out: %v", callType, err)
			return mcp.NewToolResultError(fmt.Sprintf("video generation (%s) initiation timed out", callType)), nil
		}
		log.Printf("Error initiating GenerateVideos (%s): %v", callType, err)
		return mcp.NewToolResultError(fmt.Sprintf("error starting video generation (%s): %v", callType, err)), nil
	}
	log.Printf("GenerateVideos operation (%s) initiated successfully. Operation Name: %s", callType, operation.Name)

	if progressToken != nil && mcpServer != nil {
		mcpServer.SendNotificationToClient(
			parentCtx, // Use parentCtx for notifications as it's tied to the client request
			"notifications/progress",
			map[string]interface{}{
				"progressToken": progressToken,
				"message":       fmt.Sprintf("Video generation (%s) initiated. Polling for completion...", callType),
				"status":        "initiated", // Add a status field
			},
		)
	}

	pollingStartTime := time.Now()
	pollingInterval := 15 * time.Second
	pollingAttempt := 0

	for !operation.Done {
		select {
		case <-parentCtx.Done(): // Check if the original MCP request was canceled
			log.Printf("Parent context for GenerateVideos (%s) polling canceled: %v. Stopping polling and GenAI operation.", callType, parentCtx.Err())
			operationCancel() // Attempt to cancel the GenAI operation
			return mcp.NewToolResultError(fmt.Sprintf("video generation (%s) was canceled by the client: %v", callType, parentCtx.Err())), nil
		case <-operationCtx.Done(): // Check if the GenAI operation itself timed out or was canceled
			log.Printf("Polling loop for GenerateVideos (%s) canceled/timed out by operationCtx: %v", callType, operationCtx.Err())
			return mcp.NewToolResultError(fmt.Sprintf("video generation (%s) timed out while waiting for completion", callType)), nil
		case <-time.After(pollingInterval): // Time to poll
			pollingAttempt++
			log.Printf("Polling GenerateVideos operation (%s): %s (Attempt: %d, Elapsed: %v)", callType, operation.Name, pollingAttempt, time.Since(pollingStartTime).Round(time.Second))

			// Send a proactive heartbeat notification BEFORE making the potentially slow network call.
			// This resets the client's inactivity timer.
			if progressToken != nil && mcpServer != nil {
				mcpServer.SendNotificationToClient(
					parentCtx,
					"notifications/progress",
					map[string]interface{}{
						"progressToken": progressToken,
						"message":       fmt.Sprintf("Checking video status (polling attempt %d)...", pollingAttempt),
						"status":        "polling",
					},
				)
			}

			var getOpOpts genai.GetOperationConfig
			// Use operationCtx for the GetVideosOperation call, as it's part of the GenAI operation lifecycle
			updatedOp, getErr := client.Operations.GetVideosOperation(operationCtx, operation, &getOpOpts)
			if getErr != nil {
				log.Printf("Error polling GenerateVideos operation (%s) %s: %v", callType, operation.Name, getErr)
				// If operationCtx is done, it means the GenAI operation itself was canceled or timed out.
				if errors.Is(getErr, context.Canceled) || errors.Is(getErr, context.DeadlineExceeded) {
					return mcp.NewToolResultError(fmt.Sprintf("video generation (%s) polling was canceled or timed out during GetOperation", callType)), nil
				}
				// For other errors, notify and continue (could be transient)
				if progressToken != nil && mcpServer != nil {
					mcpServer.SendNotificationToClient(
						parentCtx,
						"notifications/progress",
						map[string]interface{}{
							"progressToken": progressToken,
							"message":       fmt.Sprintf("Polling attempt %d for %s video encountered an issue. Retrying...", pollingAttempt, callType),
							"status":        "polling_issue",
						},
					)
				}
				continue // Continue polling
			}
			operation = updatedOp // Update to the latest operation status

			if progressToken != nil && mcpServer != nil {
				progressMessage := fmt.Sprintf("Video generation (%s) in progress. Polling attempt %d.", callType, pollingAttempt)
				progressPercent := -1 // Default to -1 if not available

				if operation.Metadata != nil {
					if state, ok := operation.Metadata["state"].(string); ok {
						progressMessage = fmt.Sprintf("Video generation (%s) state: %s. Polling attempt %d.", callType, state, pollingAttempt)
					}
					if p, ok := operation.Metadata["progress_percent"].(float64); ok {
						progressPercent = int(p)
						progressMessage = fmt.Sprintf("Video generation (%s) is %d%% complete. Polling attempt %d.", callType, progressPercent, pollingAttempt)
					} else if p, ok := operation.Metadata["progressPercent"].(float64); ok { // Check alternative casing
						progressPercent = int(p)
						progressMessage = fmt.Sprintf("Video generation (%s) is %d%% complete. Polling attempt %d.", callType, progressPercent, pollingAttempt)
					}
				}

				payload := map[string]interface{}{
					"progressToken": progressToken,
					"message":       progressMessage,
					"status":        "processing",
				}
				if progressPercent != -1 {
					payload["progress"] = progressPercent
					payload["total"] = 100
				}
				mcpServer.SendNotificationToClient(parentCtx, "notifications/progress", payload)
			}
		}
	}

	operationDuration := time.Since(startTime)
	log.Printf("GenerateVideos operation (%s) %s completed. Total duration: %v", callType, operation.Name, operationDuration.Round(time.Second))

	if progressToken != nil && mcpServer != nil {
		finalStatus := "completed_successfully"
		finalMessage := fmt.Sprintf("Video generation (%s) completed successfully in %v.", callType, operationDuration.Round(time.Second))
		if operation.Error != nil {
			finalStatus = "completed_with_error"
			finalMessage = fmt.Sprintf("Video generation (%s) failed after %v.", callType, operationDuration.Round(time.Second))
		}
		mcpServer.SendNotificationToClient(
			parentCtx,
			"notifications/progress",
			map[string]interface{}{
				"progressToken": progressToken,
				"message":       finalMessage,
				"status":        finalStatus,
				"progress":      100, // Mark as 100% complete
				"total":         100,
			},
		)
	}

	if operation.Error != nil {
		var errMessage string
		var errCode int32

		// Try to get structured error details if available (e.g., from google.rpc.Status)
		// The genai.Operation.Error is map[string]interface{}
		if codeVal, ok := operation.Error["code"]; ok {
			if c, okFloat := codeVal.(float64); okFloat { // JSON numbers are float64
				errCode = int32(c)
			}
		}
		if msgVal, ok := operation.Error["message"]; ok {
			if m, okStr := msgVal.(string); okStr {
				errMessage = m
			}
		}

		if errMessage == "" { // Fallback if direct fields aren't found or not of expected type
			errorBytes, jsonErr := json.Marshal(operation.Error)
			if jsonErr != nil {
				errMessage = fmt.Sprintf("operation failed with unmarshalable error: %v. Original error map: %v", jsonErr, operation.Error)
			} else {
				errMessage = string(errorBytes)
			}
		}
		log.Printf("GenerateVideos operation (%s) %s failed with error: %s (Code: %d, FullError: %v)", callType, operation.Name, errMessage, errCode, operation.Error)
		return mcp.NewToolResultError(fmt.Sprintf("video generation (%s) failed: %s (code: %d)", callType, errMessage, errCode)), nil
	}

	if operation.Response == nil || len(operation.Response.GeneratedVideos) == 0 {
		log.Printf("No videos generated (%s) by operation %s, despite successful completion.", callType, operation.Name)
		return mcp.NewToolResultText(fmt.Sprintf("Sorry, I couldn't generate any videos (%s) for your request (operation completed but no videos found).", callType)), nil
	}

	log.Printf("Successfully generated %d videos (%s) by operation %s.", len(operation.Response.GeneratedVideos), callType, operation.Name)

	var gcsVideoURIs []string
	var downloadedLocalFiles []string
	var downloadErrors []string

	for i, generatedVideo := range operation.Response.GeneratedVideos {
		videoGCSURI := ""
		if generatedVideo.Video != nil && generatedVideo.Video.URI != "" {
			videoGCSURI = generatedVideo.Video.URI
		}

		if videoGCSURI == "" {
			log.Printf("Generated video %d (%s) (model: %s, operation: %s) had no retrievable GCS URI.", i, callType, modelName, operation.Name)
			continue
		}
		gcsVideoURIs = append(gcsVideoURIs, videoGCSURI)
		log.Printf("Video %d (%s) generated by operation %s is available at GCS URI: %s", i, callType, operation.Name, videoGCSURI)

		if attemptLocalDownload {
			baseFilename := filepath.Base(videoGCSURI)
			if baseFilename == "." || baseFilename == "/" || baseFilename == "" {
				baseFilename = fmt.Sprintf("veo_video_%s_%d_%s.mp4", callType, i, time.Now().Format("20060102150405")) // More descriptive & unique fallback
			}
			localFilepath := filepath.Join(outputDir, baseFilename)
			localFilepath = filepath.Clean(localFilepath)

			log.Printf("Attempting to download video %d from GCS URI %s to %s", i, videoGCSURI, localFilepath)
			downloadErr := downloadFromGCS(parentCtx, videoGCSURI, localFilepath)
			if downloadErr != nil {
				errMsg := fmt.Sprintf("Error downloading video %d from %s to %s: %v", i, videoGCSURI, localFilepath, downloadErr)
				log.Print(errMsg)
				downloadErrors = append(downloadErrors, errMsg)
			} else {
				log.Printf("Successfully downloaded and saved video %d to %s", i, localFilepath)
				downloadedLocalFiles = append(downloadedLocalFiles, localFilepath)
			}
		}
	}

	var resultText string
	var saveMessageParts []string

	if len(gcsVideoURIs) > 0 {
		saveMessageParts = append(saveMessageParts, fmt.Sprintf("Videos saved to GCS: %s.", strings.Join(gcsVideoURIs, ", ")))
	}

	if attemptLocalDownload {
		if len(downloadedLocalFiles) > 0 { // Only mention outputDir if downloads were attempted and successful
			saveMessageParts = append(saveMessageParts, fmt.Sprintf("Successfully downloaded locally to '%s': %s.", outputDir, strings.Join(downloadedLocalFiles, ", ")))
		} else if outputDir != "" { // If outputDir was specified but no files downloaded (all errors or no videos)
			saveMessageParts = append(saveMessageParts, fmt.Sprintf("Attempted to download videos to local directory '%s'.", outputDir))
		}
		if len(downloadErrors) > 0 {
			saveMessageParts = append(saveMessageParts, fmt.Sprintf("Local download/save issues: %s.", strings.Join(downloadErrors, "; ")))
		}
	}

	if len(gcsVideoURIs) > 0 {
		resultText = fmt.Sprintf("Generated %d video(s) using model %s. This took about %s. %s",
			len(gcsVideoURIs),
			modelName,
			operationDuration.Round(time.Second),
			strings.Join(saveMessageParts, " "),
		)
	} else if operation.Error == nil {
		resultText = fmt.Sprintf("Processed request (%s) for model %s (took %s), but no video URIs were found in the completed operation %s. No specific error reported by the operation.",
			callType,
			modelName,
			operationDuration.Round(time.Second),
			operation.Name,
		)
		if len(downloadErrors) > 0 { // If there were download errors even with no GCS URIs (shouldn't happen but good to cover)
			resultText += " " + strings.Join(saveMessageParts, " ")
		}
	} else {
		// This case should ideally be caught by the operation.Error check earlier.
		// If we reach here, it implies operation.Error was non-nil but didn't lead to an early return.
		resultText = fmt.Sprintf("Video generation request (%s) for model %s (took %s) did not yield videos and encountered an issue with operation %s.",
			callType,
			modelName,
			operationDuration.Round(time.Second),
			operation.Name,
		)
		if len(downloadErrors) > 0 {
			resultText += " " + strings.Join(saveMessageParts, " ")
		}
	}

	return mcp.NewToolResultText(strings.TrimSpace(resultText)), nil
}

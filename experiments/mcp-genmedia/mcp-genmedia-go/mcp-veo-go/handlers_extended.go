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
	"log"
	"strings"

	"github.com/GoogleCloudPlatform/vertex-ai-creative-studio/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"google.golang.org/genai"
)

// veoFirstLastToVideoHandler is the handler for the 'veo_first_last_to_video' tool.
func veoFirstLastToVideoHandler(client *genai.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "veo_first_last_to_video")
	defer span.End()

	firstImageURI, ok := request.GetArguments()["first_image_uri"].(string)
	if !ok || strings.TrimSpace(firstImageURI) == "" || !strings.HasPrefix(firstImageURI, "gs://") {
		return mcp.NewToolResultError("first_image_uri must be a valid GCS URI starting with 'gs://'"), nil
	}

	lastImageURI, ok := request.GetArguments()["last_image_uri"].(string)
	if !ok || strings.TrimSpace(lastImageURI) == "" || !strings.HasPrefix(lastImageURI, "gs://") {
		return mcp.NewToolResultError("last_image_uri must be a valid GCS URI starting with 'gs://'"), nil
	}

	prompt := ""
	if promptArg, ok := request.GetArguments()["prompt"].(string); ok {
		prompt = strings.TrimSpace(promptArg)
	}

	gcsBucket, outputDir, modelName, finalAspectRatio, numberOfVideos, durationSecs, generateAudio, err := parseCommonVideoParams(request.GetArguments(), appConfig)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	modelDetails := common.SupportedVeoModels[modelName]
	if !modelDetails.SupportsFirstLast {
		return mcp.NewToolResultError(fmt.Sprintf("Model %s does not support first-last video generation.", modelName)), nil
	}

	firstMimeType := inferMimeTypeFromURI(firstImageURI)
	if firstMimeType == "" {
		firstMimeType = "image/jpeg"
	}
	lastMimeType := inferMimeTypeFromURI(lastImageURI)
	if lastMimeType == "" {
		lastMimeType = "image/jpeg"
	}

	span.SetAttributes(
		attribute.String("first_image_uri", firstImageURI),
		attribute.String("last_image_uri", lastImageURI),
		attribute.String("prompt", prompt),
		attribute.String("model", modelName),
	)

	mcpServer := server.ServerFromContext(ctx)
	var progressToken mcp.ProgressToken
	if request.Params.Meta != nil {
		progressToken = request.Params.Meta.ProgressToken
	}

	select {
	case <-ctx.Done():
		log.Printf("Incoming first_last_to_video context was already canceled: %v", ctx.Err())
		return mcp.NewToolResultError(fmt.Sprintf("request processing canceled early: %v", ctx.Err())), nil
	default:
		log.Printf("Handling Veo first_last_to_video request: FirstImageURI=\"%s\", LastImageURI=\"%s\", Prompt=\"%s\", Model=%s", firstImageURI, lastImageURI, prompt, modelName)
	}

	inputImage := &genai.Image{
		GCSURI:   firstImageURI,
		MIMEType: firstMimeType,
	}

	config := &genai.GenerateVideosConfig{
		NumberOfVideos:  numberOfVideos,
		AspectRatio:     finalAspectRatio,
		OutputGCSURI:    gcsBucket,
		DurationSeconds: &durationSecs,
		LastFrame: &genai.Image{
			GCSURI:   lastImageURI,
			MIMEType: lastMimeType,
		},
	}

	if generateAudio {
		config.GenerateAudio = &generateAudio
	}

	return callGenerateVideosAPI(client, ctx, mcpServer, progressToken, outputDir, modelName, prompt, inputImage, config, "first_last_to_video")
}

// veoReferenceToVideoHandler is the handler for the 'veo_reference_to_video' tool.
func veoReferenceToVideoHandler(client *genai.Client, ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	tr := otel.Tracer(serviceName)
	ctx, span := tr.Start(ctx, "veo_reference_to_video")
	defer span.End()

	prompt, ok := request.GetArguments()["prompt"].(string)
	if !ok || strings.TrimSpace(prompt) == "" {
		return mcp.NewToolResultError("prompt must be a non-empty string and is required for reference-to-video"), nil
	}

	referenceImageURIsRaw, ok := request.GetArguments()["reference_image_uris"].([]interface{})
	if !ok || len(referenceImageURIsRaw) == 0 {
		return mcp.NewToolResultError("reference_image_uris must be a non-empty array of strings (GCS URIs)"), nil
	}

	if len(referenceImageURIsRaw) > 3 {
		return mcp.NewToolResultError("A maximum of 3 reference images are supported"), nil
	}

	var referenceImages []*genai.VideoGenerationReferenceImage
	for _, rawURI := range referenceImageURIsRaw {
		uriStr, ok := rawURI.(string)
		if !ok || !strings.HasPrefix(uriStr, "gs://") {
			return mcp.NewToolResultError(fmt.Sprintf("Invalid reference image URI: %v. Must be a GCS URI starting with 'gs://'", rawURI)), nil
		}

		mimeType := inferMimeTypeFromURI(uriStr)
		if mimeType == "" {
			mimeType = "image/jpeg"
		}

		referenceImages = append(referenceImages, &genai.VideoGenerationReferenceImage{
			Image: &genai.Image{
				GCSURI:   uriStr,
				MIMEType: mimeType,
			},
			ReferenceType: genai.VideoGenerationReferenceTypeAsset,
		})
	}

	gcsBucket, outputDir, modelName, finalAspectRatio, numberOfVideos, durationSecs, generateAudio, err := parseCommonVideoParams(request.GetArguments(), appConfig)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	modelDetails := common.SupportedVeoModels[modelName]
	if !modelDetails.SupportsReferenceImage {
		return mcp.NewToolResultError(fmt.Sprintf("Model %s does not support reference image to video generation.", modelName)), nil
	}

	span.SetAttributes(
		attribute.String("prompt", prompt),
		attribute.String("model", modelName),
		attribute.Int("num_reference_images", len(referenceImages)),
	)

	mcpServer := server.ServerFromContext(ctx)
	var progressToken mcp.ProgressToken
	if request.Params.Meta != nil {
		progressToken = request.Params.Meta.ProgressToken
	}

	select {
	case <-ctx.Done():
		log.Printf("Incoming reference_to_video context was already canceled: %v", ctx.Err())
		return mcp.NewToolResultError(fmt.Sprintf("request processing canceled early: %v", ctx.Err())), nil
	default:
		log.Printf("Handling Veo reference_to_video request: Prompt=\"%s\", Model=%s, NumRefImages=%d", prompt, modelName, len(referenceImages))
	}

	config := &genai.GenerateVideosConfig{
		NumberOfVideos:  numberOfVideos,
		AspectRatio:     finalAspectRatio,
		OutputGCSURI:    gcsBucket,
		DurationSeconds: &durationSecs,
		ReferenceImages: referenceImages,
	}

	if generateAudio {
		config.GenerateAudio = &generateAudio
	}

	return callGenerateVideosAPI(client, ctx, mcpServer, progressToken, outputDir, modelName, prompt, nil, config, "reference_to_video")
}

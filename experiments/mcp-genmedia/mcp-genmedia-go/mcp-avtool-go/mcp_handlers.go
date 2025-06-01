package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os" // Required for MkdirTemp, WriteFile, RemoveAll
	"path/filepath"
	"strings"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"github.com/teris-io/shortid"
)

// getArguments safely extracts arguments from the MCP request.
func getArguments(request mcp.CallToolRequest) (map[string]interface{}, error) {
	if request.Params.Arguments == nil {
		log.Println("Warning: request.Params.Arguments is nil, treating as empty arguments.")
		return make(map[string]interface{}), nil
	}
	argsMap, ok := request.Params.Arguments.(map[string]interface{})
	if !ok {
		log.Printf("Error: request.Params.Arguments is of type %T, not map[string]interface{}", request.Params.Arguments)
		return nil, fmt.Errorf("internal error: request arguments are not in the expected map format (type: %T)", request.Params.Arguments)
	}
	return argsMap, nil
}

// --- FFprobe Tool Handler --- //
func addGetMediaInfoTool(s *server.MCPServer) {
	tool := mcp.NewTool("ffmpeg_get_media_info",
		mcp.WithDescription("Gets media information (streams, format, etc.) from a media file using ffprobe. Returns JSON output."),
		mcp.WithString("input_media_uri", mcp.Required(), mcp.Description("URI of the input media file (local path or gs://).")),
	)
	s.AddTool(tool, ffmpegGetMediaInfoHandler)
}

func ffmpegGetMediaInfoHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	startTime := time.Now()
	argsMap, err := getArguments(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	log.Printf("Handling %s request with arguments: %v", "ffmpeg_get_media_info", argsMap)

	inputMediaURI, _ := argsMap["input_media_uri"].(string)
	if strings.TrimSpace(inputMediaURI) == "" {
		return mcp.NewToolResultError("Parameter 'input_media_uri' is required."), nil
	}

	localInputMedia, inputCleanup, err := prepareInputFile(ctx, inputMediaURI, "media_info_input") // from file_utils.go
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input media for ffprobe: %v", err)), nil
	}
	defer inputCleanup()

	outputJSON, ffprobeErr := executeGetMediaInfo(ctx, localInputMedia) // from ffprobe_commands.go
	if ffprobeErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("FFprobe execution failed: %v. Output: %s", ffprobeErr, outputJSON)), nil
	}

	var jsTest map[string]interface{}
	if errUnmarshal := json.Unmarshal([]byte(outputJSON), &jsTest); errUnmarshal != nil {
		log.Printf("Warning: FFprobe output for %s was not valid JSON, though command reported success. Output: %s", inputMediaURI, outputJSON)
		return mcp.NewToolResultText(fmt.Sprintf("FFprobe returned non-JSON output: %s", outputJSON)), nil
	}

	duration := time.Since(startTime)
	log.Printf("FFprobe for %s completed in %v.", inputMediaURI, duration)
	return mcp.NewToolResultText(outputJSON), nil
}

// --- Convert Audio Tool Handler --- //
func addConvertAudioTool(s *server.MCPServer) {
	tool := mcp.NewTool("ffmpeg_convert_audio_wav_to_mp3",
		mcp.WithDescription("Converts a WAV audio file to MP3 format using FFMpeg."),
		mcp.WithString("input_audio_uri", mcp.Required(), mcp.Description("URI of the input WAV audio file (local path or gs://).")),
		mcp.WithString("output_file_name", mcp.Description("Optional. Desired name for the output MP3 file (e.g., 'converted.mp3'). If omitted, a unique name is generated.")),
		mcp.WithString("output_local_dir", mcp.Description("Optional. Local directory to save the output MP3 file.")),
		mcp.WithString("output_gcs_bucket", mcp.Description("Optional. GCS bucket to upload the output MP3 file to.")),
	)
	s.AddTool(tool, ffmpegConvertAudioHandler)
}

func ffmpegConvertAudioHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	startTime := time.Now()
	argsMap, err := getArguments(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	log.Printf("Handling %s request with arguments: %v", "ffmpeg_convert_audio_wav_to_mp3", argsMap)

	inputAudioURI, _ := argsMap["input_audio_uri"].(string)
	outputFileName, _ := argsMap["output_file_name"].(string)
	outputLocalDir, _ := argsMap["output_local_dir"].(string)
	outputGCSBucket, _ := argsMap["output_gcs_bucket"].(string)
	outputGCSBucket = strings.TrimSpace(outputGCSBucket)

	if outputGCSBucket == "" && genmediaBucketEnv != "" { // genmediaBucketEnv from config.go
		outputGCSBucket = genmediaBucketEnv
		log.Printf("Handler ffmpeg_convert_audio_wav_to_mp3: 'output_gcs_bucket' parameter not provided, using default from GENMEDIA_BUCKET: %s", outputGCSBucket)
	}
	if outputGCSBucket != "" {
		outputGCSBucket = strings.TrimPrefix(outputGCSBucket, "gs://")
	}
	if inputAudioURI == "" {
		return mcp.NewToolResultError("Parameter 'input_audio_uri' is required."), nil
	}

	localInputAudio, inputCleanup, err := prepareInputFile(ctx, inputAudioURI, "input_audio") // from file_utils.go
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input audio: %v", err)), nil
	}
	defer inputCleanup()

	tempOutputFile, finalOutputFilename, outputCleanup, err := handleOutputPreparation(outputFileName, "mp3") // from file_utils.go
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare output file: %v", err)), nil
	}
	defer outputCleanup()

	_, ffmpegErr := runFFmpegCommand(ctx, "-y", "-i", localInputAudio, "-acodec", "libmp3lame", tempOutputFile) // from ffmpeg_commands.go
	if ffmpegErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("FFMpeg conversion failed: %v", ffmpegErr)), nil
	}

	finalLocalPath, finalGCSPath, processErr := processOutputAfterFFmpeg(ctx, tempOutputFile, finalOutputFilename, outputLocalDir, outputGCSBucket) // from file_utils.go
	if processErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to process FFMpeg output: %v", processErr)), nil
	}

	duration := time.Since(startTime)
	var messageParts []string
	messageParts = append(messageParts, fmt.Sprintf("Audio conversion to MP3 completed in %v.", duration))
	if finalLocalPath != "" {
		if outputLocalDir != "" {
			messageParts = append(messageParts, fmt.Sprintf("Output saved locally to: %s.", finalLocalPath))
		} else {
			messageParts = append(messageParts, fmt.Sprintf("Temporary output was at: %s (cleaned up if not uploaded).", finalLocalPath))
		}
	}
	if finalGCSPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output uploaded to GCS: %s.", finalGCSPath))
	}
	if len(messageParts) == 1 {
		messageParts = append(messageParts, "No specific output location requested beyond temporary processing.")
	}
	return mcp.NewToolResultText(strings.Join(messageParts, " ")), nil
}

// --- Create GIF Tool Handler --- //
func addCreateGifTool(s *server.MCPServer) {
	tool := mcp.NewTool("ffmpeg_video_to_gif",
		mcp.WithDescription("Creates a GIF from an input video using a two-pass FFMpeg process (palette generation and palette use)."),
		mcp.WithString("input_video_uri", mcp.Required(), mcp.Description("URI of the input video file (local path or gs://).")),
		mcp.WithNumber("scale_width_factor", mcp.DefaultNumber(0.33), mcp.Description("Factor to scale the input video's width by (e.g., 0.33 for 33%). Height is scaled automatically to maintain aspect ratio. Use 1.0 for original width.")),
		mcp.WithNumber("fps", mcp.DefaultNumber(15), mcp.Min(1), mcp.Max(50), mcp.Description("Frames per second for the output GIF (e.g., 10, 15, 25).")),
		mcp.WithString("output_file_name", mcp.Description("Optional. Desired name for the output GIF file (e.g., 'animation.gif'). If omitted, a unique name is generated.")),
		mcp.WithString("output_local_dir", mcp.Description("Optional. Local directory to save the output GIF file.")),
		mcp.WithString("output_gcs_bucket", mcp.Description("Optional. GCS bucket to upload the output GIF file to (uses GENMEDIA_BUCKET if set and this is empty).")),
	)
	s.AddTool(tool, ffmpegVideoToGifHandler)
}

func ffmpegVideoToGifHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	startTime := time.Now()
	argsMap, err := getArguments(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	log.Printf("Handling %s request with arguments: %v", "ffmpeg_video_to_gif", argsMap)

	inputVideoURI, _ := argsMap["input_video_uri"].(string)
	if strings.TrimSpace(inputVideoURI) == "" {
		return mcp.NewToolResultError("Parameter 'input_video_uri' is required."), nil
	}

	scaleFactorParam, _ := argsMap["scale_width_factor"].(float64)
	if scaleFactorParam <= 0 {
		scaleFactorParam = 0.33
	}
	fpsParam, _ := argsMap["fps"].(float64)
	if fpsParam <= 0 {
		fpsParam = 15
	}
	if fpsParam < 1 {
		fpsParam = 1
	}
	if fpsParam > 50 {
		fpsParam = 50
	}

	outputFileName, _ := argsMap["output_file_name"].(string)
	outputLocalDir, _ := argsMap["output_local_dir"].(string)
	outputGCSBucket, _ := argsMap["output_gcs_bucket"].(string)
	outputGCSBucket = strings.TrimSpace(outputGCSBucket)
	if outputGCSBucket == "" && genmediaBucketEnv != "" { // genmediaBucketEnv from config.go
		outputGCSBucket = genmediaBucketEnv
		log.Printf("Handler ffmpeg_video_to_gif: 'output_gcs_bucket' parameter not provided, using default from GENMEDIA_BUCKET: %s", outputGCSBucket)
	}
	if outputGCSBucket != "" {
		outputGCSBucket = strings.TrimPrefix(outputGCSBucket, "gs://")
	}

	localInputVideo, inputCleanup, err := prepareInputFile(ctx, inputVideoURI, "input_video_for_gif") // from file_utils.go
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input video: %v", err)), nil
	}
	defer inputCleanup()

	gifProcessingTempDir, err := os.MkdirTemp("", defaultTempDirPrefix+"gif_processing_") // defaultTempDirPrefix from config.go
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to create temp directory for GIF processing: %v", err)), nil
	}
	defer func() {
		log.Printf("Cleaning up GIF processing temporary directory: %s", gifProcessingTempDir)
		os.RemoveAll(gifProcessingTempDir)
	}()

	palettePath := filepath.Join(gifProcessingTempDir, "palette.png")
	paletteVFFilter := fmt.Sprintf("fps=%.2f,scale=iw*%.2f:-1:flags=lanczos+accurate_rnd+full_chroma_inp,palettegen", fpsParam, scaleFactorParam)
	log.Printf("Generating palette with VF filter: %s", paletteVFFilter)
	_, ffmpegErrPalette := runFFmpegCommand(ctx, "-y", "-i", localInputVideo, "-vf", paletteVFFilter, palettePath) // from ffmpeg_commands.go
	if ffmpegErrPalette != nil {
		return mcp.NewToolResultError(fmt.Sprintf("FFMpeg palette generation failed: %v", ffmpegErrPalette)), nil
	}
	log.Printf("Palette generated successfully: %s", palettePath)

	var finalGifFilename string
	if strings.TrimSpace(outputFileName) == "" {
		uid, _ := shortid.Generate()
		finalGifFilename = fmt.Sprintf("ffmpeg_gif_%s.gif", uid)
	} else {
		finalGifFilename = outputFileName
		if !strings.HasSuffix(strings.ToLower(finalGifFilename), ".gif") {
			finalGifFilename += ".gif"
		}
	}
	tempGifOutputPath := filepath.Join(gifProcessingTempDir, finalGifFilename)

	gifLavfiFilter := fmt.Sprintf("fps=%.2f,scale=iw*%.2f:-1:flags=lanczos+accurate_rnd+full_chroma_inp [x]; [x][1:v] paletteuse", fpsParam, scaleFactorParam)
	log.Printf("Creating GIF with LAVFI filter: %s", gifLavfiFilter)
	_, ffmpegErrGif := runFFmpegCommand(ctx, "-y", "-i", localInputVideo, "-i", palettePath, "-lavfi", gifLavfiFilter, tempGifOutputPath) // from ffmpeg_commands.go
	if ffmpegErrGif != nil {
		return mcp.NewToolResultError(fmt.Sprintf("FFMpeg GIF creation failed: %v", ffmpegErrGif)), nil
	}
	log.Printf("GIF created successfully in temp location: %s", tempGifOutputPath)

	finalLocalPath, finalGCSPath, processErr := processOutputAfterFFmpeg(ctx, tempGifOutputPath, finalGifFilename, outputLocalDir, outputGCSBucket) // from file_utils.go
	if processErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to process generated GIF: %v", processErr)), nil
	}

	duration := time.Since(startTime)
	var messageParts []string
	messageParts = append(messageParts, fmt.Sprintf("GIF creation completed in %v.", duration.Round(time.Second)))
	if finalLocalPath != "" {
		if outputLocalDir != "" {
			messageParts = append(messageParts, fmt.Sprintf("Output GIF saved locally to: %s.", finalLocalPath))
		} else if !(outputGCSBucket != "" && finalGCSPath != "") {
			messageParts = append(messageParts, fmt.Sprintf("Temporary GIF output was at: %s (cleaned up if not moved/uploaded).", finalLocalPath))
		}
	}
	if finalGCSPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output GIF uploaded to GCS: %s.", finalGCSPath))
	}
	if len(messageParts) == 1 {
		messageParts = append(messageParts, "No specific output location (local/GCS) was processed or an issue occurred in processing.")
	}
	return mcp.NewToolResultText(strings.Join(messageParts, " ")), nil
}

// --- Combine Audio/Video Tool Handler --- //
func addCombineAudioVideoTool(s *server.MCPServer) {
	tool := mcp.NewTool("ffmpeg_combine_audio_and_video",
		mcp.WithDescription("Combines separate audio and video files into a single video file."),
		mcp.WithString("input_video_uri", mcp.Required(), mcp.Description("URI of the input video file (local path or gs://).")),
		mcp.WithString("input_audio_uri", mcp.Required(), mcp.Description("URI of the input audio file (local path or gs://).")),
		mcp.WithString("output_file_name", mcp.Description("Optional. Desired name for the output video file (e.g., 'combined.mp4').")),
		mcp.WithString("output_local_dir", mcp.Description("Optional. Local directory to save the output video file.")),
		mcp.WithString("output_gcs_bucket", mcp.Description("Optional. GCS bucket to upload the output video file to.")),
	)
	s.AddTool(tool, ffmpegCombineAudioVideoHandler)
}

func ffmpegCombineAudioVideoHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	startTime := time.Now()
	argsMap, err := getArguments(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	log.Printf("Handling %s request with arguments: %v", "ffmpeg_combine_audio_and_video", argsMap)

	inputVideoURI, _ := argsMap["input_video_uri"].(string)
	inputAudioURI, _ := argsMap["input_audio_uri"].(string)
	outputFileName, _ := argsMap["output_file_name"].(string)
	outputLocalDir, _ := argsMap["output_local_dir"].(string)
	outputGCSBucket, _ := argsMap["output_gcs_bucket"].(string)
	outputGCSBucket = strings.TrimSpace(outputGCSBucket)

	if outputGCSBucket == "" && genmediaBucketEnv != "" { // genmediaBucketEnv from config.go
		outputGCSBucket = genmediaBucketEnv
		log.Printf("Handler ffmpeg_combine_audio_and_video: 'output_gcs_bucket' parameter not provided, using default from GENMEDIA_BUCKET: %s", outputGCSBucket)
	}
	if outputGCSBucket != "" {
		outputGCSBucket = strings.TrimPrefix(outputGCSBucket, "gs://")
	}
	if inputVideoURI == "" || inputAudioURI == "" {
		return mcp.NewToolResultError("Parameters 'input_video_uri' and 'input_audio_uri' are required."), nil
	}

	localInputVideo, videoCleanup, err := prepareInputFile(ctx, inputVideoURI, "input_video") // from file_utils.go
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input video: %v", err)), nil
	}
	defer videoCleanup()

	localInputAudio, audioCleanup, err := prepareInputFile(ctx, inputAudioURI, "input_audio") // from file_utils.go
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input audio: %v", err)), nil
	}
	defer audioCleanup()

	tempOutputFile, finalOutputFilename, outputCleanup, err := handleOutputPreparation(outputFileName, "mp4") // from file_utils.go
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare output file: %v", err)), nil
	}
	defer outputCleanup()

	_, ffmpegErr := runFFmpegCommand(ctx, "-y", "-i", localInputVideo, "-i", localInputAudio, "-map", "0", "-map", "1:a", "-c:v", "copy", "-shortest", tempOutputFile) // from ffmpeg_commands.go
	if ffmpegErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("FFMpeg combine audio/video failed: %v", ffmpegErr)), nil
	}

	finalLocalPath, finalGCSPath, processErr := processOutputAfterFFmpeg(ctx, tempOutputFile, finalOutputFilename, outputLocalDir, outputGCSBucket) // from file_utils.go
	if processErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to process FFMpeg output: %v", processErr)), nil
	}

	duration := time.Since(startTime)
	var messageParts []string
	messageParts = append(messageParts, fmt.Sprintf("Audio and video combination completed in %v.", duration))
	if outputLocalDir != "" && finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output saved locally to: %s.", finalLocalPath))
	} else if finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Temporary output was at: %s (cleaned up if not moved/uploaded).", finalLocalPath))
	}
	if finalGCSPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output uploaded to GCS: %s.", finalGCSPath))
	}
	if len(messageParts) == 1 {
		messageParts = append(messageParts, "No specific output location requested beyond temporary processing.")
	}
	return mcp.NewToolResultText(strings.Join(messageParts, " ")), nil
}

// --- Overlay Image on Video Tool Handler --- //
func addOverlayImageOnVideoTool(s *server.MCPServer) {
	tool := mcp.NewTool("ffmpeg_overlay_image_on_video",
		mcp.WithDescription("Overlays an image onto a video at specified coordinates."),
		mcp.WithString("input_video_uri", mcp.Required(), mcp.Description("URI of the input video file (local path or gs://).")),
		mcp.WithString("input_image_uri", mcp.Required(), mcp.Description("URI of the input image file (local path or gs://).")),
		mcp.WithNumber("x_coordinate", mcp.DefaultNumber(0), mcp.Description("X coordinate for the overlay (top-left).")),
		mcp.WithNumber("y_coordinate", mcp.DefaultNumber(0), mcp.Description("Y coordinate for the overlay (top-left).")),
		mcp.WithString("output_file_name", mcp.Description("Optional. Desired name for the output video file (e.g., 'overlayed_video.mp4').")),
		mcp.WithString("output_local_dir", mcp.Description("Optional. Local directory to save the output video file.")),
		mcp.WithString("output_gcs_bucket", mcp.Description("Optional. GCS bucket to upload the output video file to.")),
	)
	s.AddTool(tool, ffmpegOverlayImageHandler)
}

func ffmpegOverlayImageHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	startTime := time.Now()
	argsMap, err := getArguments(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	log.Printf("Handling %s request with arguments: %v", "ffmpeg_overlay_image_on_video", argsMap)

	inputVideoURI, _ := argsMap["input_video_uri"].(string)
	inputImageURI, _ := argsMap["input_image_uri"].(string)
	xCoordFloat, _ := argsMap["x_coordinate"].(float64)
	yCoordFloat, _ := argsMap["y_coordinate"].(float64)
	xCoord := int(xCoordFloat)
	yCoord := int(yCoordFloat)
	outputFileName, _ := argsMap["output_file_name"].(string)
	outputLocalDir, _ := argsMap["output_local_dir"].(string)
	outputGCSBucket, _ := argsMap["output_gcs_bucket"].(string)
	outputGCSBucket = strings.TrimSpace(outputGCSBucket)

	if outputGCSBucket == "" && genmediaBucketEnv != "" { // genmediaBucketEnv from config.go
		outputGCSBucket = genmediaBucketEnv
		log.Printf("Handler ffmpeg_overlay_image_on_video: 'output_gcs_bucket' parameter not provided, using default from GENMEDIA_BUCKET: %s", outputGCSBucket)
	}
	if outputGCSBucket != "" {
		outputGCSBucket = strings.TrimPrefix(outputGCSBucket, "gs://")
	}
	if inputVideoURI == "" || inputImageURI == "" {
		return mcp.NewToolResultError("Parameters 'input_video_uri' and 'input_image_uri' are required."), nil
	}

	localInputVideo, videoCleanup, err := prepareInputFile(ctx, inputVideoURI, "input_video") // from file_utils.go
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input video: %v", err)), nil
	}
	defer videoCleanup()

	localInputImage, imageCleanup, err := prepareInputFile(ctx, inputImageURI, "input_image") // from file_utils.go
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input image: %v", err)), nil
	}
	defer imageCleanup()

	tempOutputFile, finalOutputFilename, outputCleanup, err := handleOutputPreparation(outputFileName, "mp4") // from file_utils.go
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare output file: %v", err)), nil
	}
	defer outputCleanup()

	overlayFilter := fmt.Sprintf("[0:v][1:v]overlay=%d:%d", xCoord, yCoord)
	_, ffmpegErr := runFFmpegCommand(ctx, "-y", "-i", localInputVideo, "-i", localInputImage, "-filter_complex", overlayFilter, tempOutputFile) // from ffmpeg_commands.go
	if ffmpegErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("FFMpeg overlay image failed: %v", ffmpegErr)), nil
	}

	finalLocalPath, finalGCSPath, processErr := processOutputAfterFFmpeg(ctx, tempOutputFile, finalOutputFilename, outputLocalDir, outputGCSBucket) // from file_utils.go
	if processErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to process FFMpeg output: %v", processErr)), nil
	}

	duration := time.Since(startTime)
	var messageParts []string
	messageParts = append(messageParts, fmt.Sprintf("Image overlay on video completed in %v.", duration))
	if outputLocalDir != "" && finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output saved locally to: %s.", finalLocalPath))
	} else if finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Temporary output was at: %s (cleaned up if not moved/uploaded).", finalLocalPath))
	}
	if finalGCSPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output uploaded to GCS: %s.", finalGCSPath))
	}
	if len(messageParts) == 1 {
		messageParts = append(messageParts, "No specific output location requested beyond temporary processing.")
	}
	return mcp.NewToolResultText(strings.Join(messageParts, " ")), nil
}

// --- Concatenate Media Tool Handler --- //
func addConcatenateMediaTool(s *server.MCPServer) {
	tool := mcp.NewTool("ffmpeg_concatenate_media_files",
		mcp.WithDescription("Concatenates multiple media files. If output is WAV, inputs must be PCM WAV; otherwise, inputs are standardized to MP4/AAC before concatenation."),
		mcp.WithArray("input_media_uris", mcp.Required(), mcp.Description("Array of URIs for the input media files (local paths or gs://).")),
		mcp.WithString("output_file_name", mcp.Description("Optional. Desired name for the output file (e.g., 'concatenated.mp4'). Extension determines behavior for audio concatenation.")),
		mcp.WithString("output_local_dir", mcp.Description("Optional. Local directory to save the output file.")),
		mcp.WithString("output_gcs_bucket", mcp.Description("Optional. GCS bucket to upload the output file to.")),
	)
	s.AddTool(tool, ffmpegConcatenateMediaHandler)
}

func ffmpegConcatenateMediaHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	startTime := time.Now()
	argsMap, err := getArguments(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	log.Printf("Handling %s request with arguments: %v", "ffmpeg_concatenate_media_files", argsMap)

	inputMediaURIsRaw, _ := argsMap["input_media_uris"].([]interface{})
	var inputMediaURIs []string
	for _, item := range inputMediaURIsRaw {
		if strItem, ok := item.(string); ok {
			inputMediaURIs = append(inputMediaURIs, strItem)
		}
	}

	outputFileName, _ := argsMap["output_file_name"].(string)
	outputLocalDir, _ := argsMap["output_local_dir"].(string)
	outputGCSBucket, _ := argsMap["output_gcs_bucket"].(string)
	outputGCSBucket = strings.TrimSpace(outputGCSBucket)

	if outputGCSBucket == "" && genmediaBucketEnv != "" {
		outputGCSBucket = genmediaBucketEnv
		log.Printf("Handler ffmpeg_concatenate_media_files: 'output_gcs_bucket' parameter not provided, using default from GENMEDIA_BUCKET: %s", outputGCSBucket)
	}
	if outputGCSBucket != "" {
		outputGCSBucket = strings.TrimPrefix(outputGCSBucket, "gs://")
	}
	if len(inputMediaURIs) < 1 { // Allow single file "concatenation" for consistent processing if desired, though typically 2+
		if len(inputMediaURIs) == 0 {
			return mcp.NewToolResultError("At least one media file is required for concatenation."), nil
		}
		log.Println("Warning: Only one input file provided for concatenation. Will process it as a single file operation.")
	}
	if len(inputMediaURIs) < 2 && len(inputMediaURIs) > 0 {
		log.Println("Warning: Only one input file provided for concatenation. The 'concatenation' will essentially be a copy or re-encode of this single file through the chosen path (PCM or AAC standardization).")
	}

	var localInputFilePaths []string
	var inputCleanups []func()
	defer func() {
		for _, c := range inputCleanups {
			c()
		}
	}()

	for i, uri := range inputMediaURIs {
		localPath, cleanup, errPrep := prepareInputFile(ctx, uri, fmt.Sprintf("concat_input_%d", i))
		if errPrep != nil {
			return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input media file %s: %v", uri, errPrep)), nil
		}
		inputCleanups = append(inputCleanups, cleanup)
		localInputFilePaths = append(localInputFilePaths, localPath)
	}

	defaultOutputExt := "mp4" // Default for video or mixed content
	if len(localInputFilePaths) > 0 {
		// Try to infer from first input if it's a common audio type
		firstExt := strings.ToLower(strings.TrimPrefix(filepath.Ext(localInputFilePaths[0]), "."))
		if firstExt == "wav" || firstExt == "mp3" || firstExt == "aac" || firstExt == "m4a" {
			defaultOutputExt = firstExt
		}
	}
	if outputFileName != "" { // User-specified output name takes precedence for extension
		userExt := strings.ToLower(strings.TrimPrefix(filepath.Ext(outputFileName), "."))
		if userExt != "" {
			defaultOutputExt = userExt
		}
	}

	tempOutputFile, finalOutputFilename, outputProcessingCleanup, err := handleOutputPreparation(outputFileName, defaultOutputExt)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare output file: %v", err)), nil
	}
	defer outputProcessingCleanup()

	isOutputWav := strings.ToLower(defaultOutputExt) == "wav"

	if isOutputWav {
		log.Println("Output is WAV. Checking if all inputs are compatible PCM WAV for direct concatenation.")
		allInputsAreCompatiblePcmWav := true // Assume true initially
		var firstPcmInfo struct { // Store properties of the first PCM WAV encountered
			SampleFmt    string
			SampleRate   string
			Channels     int
			CodecName    string
			Initialized  bool
		}
		var actualPcmInputPaths []string

		if len(localInputFilePaths) == 0 {
			allInputsAreCompatiblePcmWav = false // No inputs to check
		}

		for i, path := range localInputFilePaths {
			log.Printf("Checking codec and properties for input %d: %s", i+1, path)
			mediaInfoJSON, ffprobeErr := executeGetMediaInfo(ctx, path)
			if ffprobeErr != nil {
				allInputsAreCompatiblePcmWav = false
				log.Printf("Failed to get media info for input %s: %v. Cannot ensure PCM WAV compatibility.", path, ffprobeErr)
				break
			}

			var info struct {
				Streams []struct {
					CodecType   string `json:"codec_type"`
					CodecName   string `json:"codec_name"`
					SampleFmt   string `json:"sample_fmt"`
					SampleRate  string `json:"sample_rate"`
					Channels    int    `json:"channels"`
				} `json:"streams"`
			}
			if err := json.Unmarshal([]byte(mediaInfoJSON), &info); err != nil {
				allInputsAreCompatiblePcmWav = false
				log.Printf("Failed to parse media info for input %s: %v. Cannot ensure PCM WAV compatibility.", path, err)
				break
			}

			isCurrentFilePcm := false
			var currentStreamInfo struct { // Temporary for current file's audio stream
				SampleFmt  string
				SampleRate string
				Channels   int
				CodecName  string
			}
			audioStreamFound := false

			for _, stream := range info.Streams {
				if stream.CodecType == "audio" {
					audioStreamFound = true
					log.Printf("Audio stream found for %s: codec_name='%s', sample_fmt='%s', sample_rate='%s', channels=%d",
						path, stream.CodecName, stream.SampleFmt, stream.SampleRate, stream.Channels)
					if strings.HasPrefix(stream.CodecName, "pcm_") {
						isCurrentFilePcm = true
						currentStreamInfo.SampleFmt = stream.SampleFmt
						currentStreamInfo.SampleRate = stream.SampleRate
						currentStreamInfo.Channels = stream.Channels
						currentStreamInfo.CodecName = stream.CodecName
					} else {
						isCurrentFilePcm = false // Found an audio stream, but it's not PCM
					}
					break // Process first audio stream only
				}
			}

			if !audioStreamFound {
				allInputsAreCompatiblePcmWav = false
				log.Printf("No audio stream found in input %s. Cannot treat as compatible PCM WAV.", path)
				break
			}
			if !isCurrentFilePcm {
				allInputsAreCompatiblePcmWav = false
				log.Printf("Input file %s is not PCM WAV (audio codec: %s).", path, currentStreamInfo.CodecName)
				break
			}

			// Now, if it IS PCM, check for compatibility
			if !firstPcmInfo.Initialized {
				firstPcmInfo.SampleFmt = currentStreamInfo.SampleFmt
				firstPcmInfo.SampleRate = currentStreamInfo.SampleRate
				firstPcmInfo.Channels = currentStreamInfo.Channels
				firstPcmInfo.CodecName = currentStreamInfo.CodecName
				firstPcmInfo.Initialized = true
				log.Printf("First PCM WAV input %s (%s) sets standard: SR=%s, Fmt=%s, Ch=%d",
					path, firstPcmInfo.CodecName, firstPcmInfo.SampleRate, firstPcmInfo.SampleFmt, firstPcmInfo.Channels)
			} else {
				// Compare with the first PCM file's properties
				if currentStreamInfo.SampleRate != firstPcmInfo.SampleRate ||
					currentStreamInfo.Channels != firstPcmInfo.Channels ||
					currentStreamInfo.SampleFmt != firstPcmInfo.SampleFmt {
					allInputsAreCompatiblePcmWav = false
					log.Printf("Input PCM WAV file %s (%s, SR=%s, Fmt=%s, Ch=%d) is incompatible with the first PCM WAV file (%s, SR=%s, Fmt=%s, Ch=%d).",
						path, currentStreamInfo.CodecName, currentStreamInfo.SampleRate, currentStreamInfo.SampleFmt, currentStreamInfo.Channels,
						firstPcmInfo.CodecName, firstPcmInfo.SampleRate, firstPcmInfo.SampleFmt, firstPcmInfo.Channels)
					break
				}
				log.Printf("Input PCM WAV file %s is compatible with the first.", path)
			}
			actualPcmInputPaths = append(actualPcmInputPaths, path)
		} // End of loop through input files

		if allInputsAreCompatiblePcmWav && firstPcmInfo.Initialized { // Ensure at least one PCM file was processed
			log.Println("All inputs are compatible PCM WAV. Proceeding with direct PCM concatenation.")

			concatListTempDir, errListTempDir := os.MkdirTemp("", defaultTempDirPrefix+"concat_list_pcm_")
			if errListTempDir != nil {
				return mcp.NewToolResultError(fmt.Sprintf("Failed to create temp dir for PCM concat list: %v", errListTempDir)), nil
			}
			defer func() {
				log.Printf("Cleaning up PCM concat list temporary directory: %s", concatListTempDir)
				os.RemoveAll(concatListTempDir)
			}()

			concatListPath := filepath.Join(concatListTempDir, "concat_list_pcm.txt")
			var fileListContent strings.Builder
			for _, pcmPath := range actualPcmInputPaths {
				absPath, absErr := filepath.Abs(pcmPath)
				if absErr != nil {
					return mcp.NewToolResultError(fmt.Sprintf("Failed to get absolute path for PCM file %s: %v", pcmPath, absErr)), nil
				}
				fileListContent.WriteString(fmt.Sprintf("file '%s'\n", absPath))
			}
			if errWriteList := os.WriteFile(concatListPath, []byte(fileListContent.String()), 0644); errWriteList != nil {
				return mcp.NewToolResultError(fmt.Sprintf("Failed to write PCM concat list file: %v", errWriteList)), nil
			}

			concatCmdArgs := []string{"-y", "-f", "concat", "-safe", "0", "-i", concatListPath, "-c", "copy", tempOutputFile}
			log.Printf("Attempting direct PCM concatenation of WAV files using concat demuxer (-c copy).")
			_, ffmpegErr := runFFmpegCommand(ctx, concatCmdArgs...)
			if ffmpegErr != nil {
				return mcp.NewToolResultError(fmt.Sprintf("FFMpeg direct PCM WAV concatenation failed: %v. Ensure input WAVs have compatible PCM formats (sample rate, channels, bit depth).", ffmpegErr)), nil
			}
			log.Println("Direct PCM WAV concatenation successful.")

		} else {
			log.Println("Output is WAV, but not all inputs are compatible PCM WAV, or an error occurred checking. Rejecting operation.")
			return mcp.NewToolResultError("Error: When outputting to WAV, all input files must be PCM WAV with identical characteristics (sample rate, sample format, and channel count). Please convert inputs to a common PCM WAV format or choose a different output format (e.g., M4A, MP4)."), nil
		}

	} else { // Output is NOT WAV (e.g., mp4, m4a) - use existing AAC standardization logic
		log.Println("Output is not WAV. Proceeding with standardization to MP4/AAC before concatenation.")
		var standardizedFiles []string
		standardizationTempDir, errStdTempDir := os.MkdirTemp("", defaultTempDirPrefix+"concat_standardize_")
		if errStdTempDir != nil {
			return mcp.NewToolResultError(fmt.Sprintf("Failed to create temp dir for standardization: %v", errStdTempDir)), nil
		}
		defer func() {
			log.Printf("Cleaning up standardization temporary directory: %s", standardizationTempDir)
			os.RemoveAll(standardizationTempDir)
		}()

		commonWidth := 1280 // Example, adjust as needed or make configurable
		commonHeight := 720
		commonFPS := "24"
		commonSampleRate := "48000"
		commonChannels := "2"

		for i, localInputFile := range localInputFilePaths {
			baseName := filepath.Base(localInputFile)
			ext := filepath.Ext(baseName)
			standardizedOutputName := fmt.Sprintf("standardized_%d_%s.mp4", i, strings.TrimSuffix(baseName, ext))
			standardizedOutputPath := filepath.Join(standardizationTempDir, standardizedOutputName)

			// Check if input is audio-only. If so, skip video filters.
			mediaInfoJSON, ffprobeErr := executeGetMediaInfo(ctx, localInputFile)
			isAudioOnly := false
			if ffprobeErr == nil {
				var info struct {
					Streams []struct {
						CodecType string `json:"codec_type"`
					} `json:"streams"`
				}
				if json.Unmarshal([]byte(mediaInfoJSON), &info) == nil {
					hasVideo := false
					for _, s := range info.Streams {
						if s.CodecType == "video" {
							hasVideo = true
							break
						}
					}
					if !hasVideo && len(info.Streams) > 0 {
						isAudioOnly = true
					}
				}
			}

			var standardizeCmdArgs []string
			if isAudioOnly {
				log.Printf("Standardizing audio-only input %d ('%s') to AAC in MP4 container: '%s'", i+1, localInputFile, standardizedOutputPath)
				standardizeCmdArgs = []string{"-y", "-i", localInputFile, "-vn", "-c:a", "aac", "-ar", commonSampleRate, "-ac", commonChannels, "-b:a", "192k", standardizedOutputPath}
			} else {
				log.Printf("Standardizing video/mixed input %d ('%s') to H264/AAC in MP4 container: '%s'", i+1, localInputFile, standardizedOutputPath)
				vfArgs := fmt.Sprintf("scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:0:0,fps=%s", commonWidth, commonHeight, commonWidth, commonHeight, commonFPS)
				standardizeCmdArgs = []string{"-y", "-i", localInputFile, "-vf", vfArgs, "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac", "-ar", commonSampleRate, "-ac", commonChannels, "-b:a", "192k", standardizedOutputPath}
			}

			_, stdErr := runFFmpegCommand(ctx, standardizeCmdArgs...)
			if stdErr != nil {
				return mcp.NewToolResultError(fmt.Sprintf("Failed to standardize file %s: %v", localInputFile, stdErr)), nil
			}
			standardizedFiles = append(standardizedFiles, standardizedOutputPath)
		}

		if len(standardizedFiles) == 0 { // Should be at least one if localInputFilePaths was not empty
			return mcp.NewToolResultError("No files were successfully standardized for concatenation."), nil
		}

		concatListTempDir, errListTempDir := os.MkdirTemp("", defaultTempDirPrefix+"concat_list_std_")
		if errListTempDir != nil {
			return mcp.NewToolResultError(fmt.Sprintf("Failed to create temp dir for standardized concat list: %v", errListTempDir)), nil
		}
		defer func() {
			log.Printf("Cleaning up standardized concat list temporary directory: %s", concatListTempDir)
			os.RemoveAll(concatListTempDir)
		}()

		concatListPath := filepath.Join(concatListTempDir, "concat_list_std.txt")
		var fileListContent strings.Builder
		for _, sf := range standardizedFiles {
			absPath, absErr := filepath.Abs(sf)
			if absErr != nil {
				return mcp.NewToolResultError(fmt.Sprintf("Failed to get absolute path for standardized file %s: %v", sf, absErr)), nil
			}
			fileListContent.WriteString(fmt.Sprintf("file '%s'\n", absPath))
		}
		if errWriteList := os.WriteFile(concatListPath, []byte(fileListContent.String()), 0644); errWriteList != nil {
			return mcp.NewToolResultError(fmt.Sprintf("Failed to write standardized concat list file: %v", errWriteList)), nil
		}

		concatDemuxerCmdArgs := []string{"-y", "-f", "concat", "-safe", "0", "-i", concatListPath, "-c", "copy", tempOutputFile}
		log.Printf("Attempting concatenation of standardized files using concat demuxer (-c copy).")
		_, ffmpegErr := runFFmpegCommand(ctx, concatDemuxerCmdArgs...)
		if ffmpegErr != nil {
			return mcp.NewToolResultError(fmt.Sprintf("FFMpeg concatenation (concat demuxer with -c copy) failed: %v", ffmpegErr)), nil
		}
		log.Println("Concatenation of standardized files successful.")
	}

	// Common output processing for both WAV and non-WAV paths
	finalLocalPath, finalGCSPath, processErr := processOutputAfterFFmpeg(ctx, tempOutputFile, finalOutputFilename, outputLocalDir, outputGCSBucket)
	if processErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to process FFMpeg output: %v", processErr)), nil
	}

	duration := time.Since(startTime)
	var messageParts []string
	messageParts = append(messageParts, fmt.Sprintf("Media concatenation completed in %v.", duration))
	if outputLocalDir != "" && finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output saved locally to: %s.", finalLocalPath))
	} else if finalLocalPath != "" && !(outputGCSBucket != "" && finalGCSPath != "") { // Avoid saying temp if it was uploaded
		messageParts = append(messageParts, fmt.Sprintf("Temporary output was at: %s (cleaned up if not moved/uploaded).", finalLocalPath))
	}
	if finalGCSPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output uploaded to GCS: %s.", finalGCSPath))
	}
	if len(messageParts) == 1 {
		messageParts = append(messageParts, "No specific output location requested beyond temporary processing, or an issue occurred.")
	}
	return mcp.NewToolResultText(strings.Join(messageParts, " ")), nil
}

// --- Adjust Volume Tool Handler --- //
func addAdjustVolumeTool(s *server.MCPServer) {
	tool := mcp.NewTool("ffmpeg_adjust_volume",
		mcp.WithDescription("Adjusts the volume of an audio file by a specified dB amount."),
		mcp.WithString("input_audio_uri", mcp.Required(), mcp.Description("URI of the input audio file (local path or gs://).")),
		mcp.WithNumber("volume_db_change", mcp.Required(), mcp.Description("Volume change in dB (e.g., -10 for -10dB, 5 for +5dB).")),
		mcp.WithString("output_file_name", mcp.Description("Optional. Desired name for the output audio file.")),
		mcp.WithString("output_local_dir", mcp.Description("Optional. Local directory to save the output audio file.")),
		mcp.WithString("output_gcs_bucket", mcp.Description("Optional. GCS bucket to upload the output audio file to.")),
	)
	s.AddTool(tool, ffmpegAdjustVolumeHandler)
}

func ffmpegAdjustVolumeHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	startTime := time.Now()
	argsMap, err := getArguments(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	log.Printf("Handling %s request with arguments: %v", "ffmpeg_adjust_volume", argsMap)

	inputAudioURI, _ := argsMap["input_audio_uri"].(string)
	volumeDBChangeFloat, paramOK := argsMap["volume_db_change"].(float64)
	if !paramOK {
		return mcp.NewToolResultError("Parameter 'volume_db_change' is required and must be a number."), nil
	}
	volumeDBChange := int(volumeDBChangeFloat) // FFMpeg volume filter usually takes integer dB
	outputFileName, _ := argsMap["output_file_name"].(string)
	outputLocalDir, _ := argsMap["output_local_dir"].(string)
	outputGCSBucket, _ := argsMap["output_gcs_bucket"].(string)
	outputGCSBucket = strings.TrimSpace(outputGCSBucket)

	if outputGCSBucket == "" && genmediaBucketEnv != "" { // genmediaBucketEnv from config.go
		outputGCSBucket = genmediaBucketEnv
		log.Printf("Handler ffmpeg_adjust_volume: 'output_gcs_bucket' parameter not provided, using default from GENMEDIA_BUCKET: %s", outputGCSBucket)
	}
	if outputGCSBucket != "" {
		outputGCSBucket = strings.TrimPrefix(outputGCSBucket, "gs://")
	}
	if inputAudioURI == "" {
		return mcp.NewToolResultError("Parameter 'input_audio_uri' is required."), nil
	}

	localInputAudio, inputCleanup, err := prepareInputFile(ctx, inputAudioURI, "input_audio_vol") // from file_utils.go
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input audio: %v", err)), nil
	}
	defer inputCleanup()

	defaultOutputExt := "mp3" // Default if not inferable
	inputExt := strings.ToLower(strings.TrimPrefix(filepath.Ext(localInputAudio), "."))
	if inputExt != "" { // Try to keep original extension if known audio type
		switch inputExt {
		case "wav", "mp3", "aac", "m4a", "ogg", "flac":
			defaultOutputExt = inputExt
		}
	}
	if outputFileName != "" { // User-specified output name takes precedence for extension
		userExt := strings.ToLower(strings.TrimPrefix(filepath.Ext(outputFileName), "."))
		if userExt != "" {
			defaultOutputExt = userExt
		}
	}

	tempOutputFile, finalOutputFilename, outputCleanup, err := handleOutputPreparation(outputFileName, defaultOutputExt) // from file_utils.go
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare output file: %v", err)), nil
	}
	defer outputCleanup()

	volumeFilter := fmt.Sprintf("volume=%ddB", volumeDBChange)
	_, ffmpegErr := runFFmpegCommand(ctx, "-y", "-i", localInputAudio, "-af", volumeFilter, tempOutputFile) // from ffmpeg_commands.go
	if ffmpegErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("FFMpeg adjust volume failed: %v", ffmpegErr)), nil
	}

	finalLocalPath, finalGCSPath, processErr := processOutputAfterFFmpeg(ctx, tempOutputFile, finalOutputFilename, outputLocalDir, outputGCSBucket) // from file_utils.go
	if processErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to process FFMpeg output: %v", processErr)), nil
	}

	duration := time.Since(startTime)
	var messageParts []string
	messageParts = append(messageParts, fmt.Sprintf("Volume adjustment (%ddB) completed in %v.", volumeDBChange, duration))
	if outputLocalDir != "" && finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output saved locally to: %s.", finalLocalPath))
	} else if finalLocalPath != "" && !(outputGCSBucket != "" && finalGCSPath != "") {
		messageParts = append(messageParts, fmt.Sprintf("Temporary output was at: %s (cleaned up if not moved/uploaded).", finalLocalPath))
	}
	if finalGCSPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output uploaded to GCS: %s.", finalGCSPath))
	}
	if len(messageParts) == 1 {
		messageParts = append(messageParts, "No specific output location requested beyond temporary processing.")
	}
	return mcp.NewToolResultText(strings.Join(messageParts, " ")), nil
}

// --- Layer Audio Tool Handler --- //
func addLayerAudioTool(s *server.MCPServer) {
	tool := mcp.NewTool("ffmpeg_layer_audio_files",
		mcp.WithDescription("Layers multiple audio files together (mixing)."),
		mcp.WithArray("input_audio_uris", mcp.Required(), mcp.Description("Array of URIs for the input audio files to layer (local paths or gs://).")),
		mcp.WithString("output_file_name", mcp.Description("Optional. Desired name for the output mixed audio file (e.g., 'layered_audio.mp3').")),
		mcp.WithString("output_local_dir", mcp.Description("Optional. Local directory to save the output file.")),
		mcp.WithString("output_gcs_bucket", mcp.Description("Optional. GCS bucket to upload the output file to.")),
	)
	s.AddTool(tool, ffmpegLayerAudioHandler)
}

func ffmpegLayerAudioHandler(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	startTime := time.Now()
	argsMap, err := getArguments(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	log.Printf("Handling %s request with arguments: %v", "ffmpeg_layer_audio_files", argsMap)

	inputAudioURIsRaw, _ := argsMap["input_audio_uris"].([]interface{})
	var inputAudioURIs []string
	for _, item := range inputAudioURIsRaw {
		if strItem, ok := item.(string); ok {
			inputAudioURIs = append(inputAudioURIs, strItem)
		}
	}

	outputFileName, _ := argsMap["output_file_name"].(string)
	outputLocalDir, _ := argsMap["output_local_dir"].(string)
	outputGCSBucket, _ := argsMap["output_gcs_bucket"].(string)
	outputGCSBucket = strings.TrimSpace(outputGCSBucket)

	if outputGCSBucket == "" && genmediaBucketEnv != "" { // genmediaBucketEnv from config.go
		outputGCSBucket = genmediaBucketEnv
		log.Printf("Handler ffmpeg_layer_audio_files: 'output_gcs_bucket' parameter not provided, using default from GENMEDIA_BUCKET: %s", outputGCSBucket)
	}
	if outputGCSBucket != "" {
		outputGCSBucket = strings.TrimPrefix(outputGCSBucket, "gs://")
	}
	if len(inputAudioURIs) < 1 { // Allow single file for consistency, though amix usually needs 2+
		if len(inputAudioURIs) == 0 {
			return mcp.NewToolResultError("At least one audio file is required for layering."), nil
		}
		log.Println("Warning: Only one input file provided for layering. The 'layering' will essentially be a copy or re-encode of this single file.")
	}

	var localInputFiles []string
	var inputCleanups []func()
	defer func() {
		for _, c := range inputCleanups {
			c()
		}
	}()

	var ffmpegInputArgs []string
	for i, uri := range inputAudioURIs {
		localPath, cleanup, errPrep := prepareInputFile(ctx, uri, fmt.Sprintf("layer_input_%d", i)) // from file_utils.go
		if errPrep != nil {
			return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare input audio file %s: %v", uri, errPrep)), nil
		}
		inputCleanups = append(inputCleanups, cleanup)
		localInputFiles = append(localInputFiles, localPath)
		ffmpegInputArgs = append(ffmpegInputArgs, "-i", localPath)
	}

	defaultOutputExt := "mp3"     // Default for layered audio
	if len(localInputFiles) > 0 { // Try to infer from first input if common audio
		firstExt := strings.ToLower(strings.TrimPrefix(filepath.Ext(localInputFiles[0]), "."))
		if firstExt == "wav" || firstExt == "mp3" || firstExt == "aac" || firstExt == "m4a" {
			defaultOutputExt = firstExt
		}
	}
	if outputFileName != "" { // User-specified output name takes precedence for extension
		userExt := strings.ToLower(strings.TrimPrefix(filepath.Ext(outputFileName), "."))
		if userExt != "" {
			defaultOutputExt = userExt
		}
	}

	tempOutputFile, finalOutputFilename, outputCleanup, err := handleOutputPreparation(outputFileName, defaultOutputExt) // from file_utils.go
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to prepare output file: %v", err)), nil
	}
	defer outputCleanup()

	var commandArgs []string
	commandArgs = append(commandArgs, "-y")
	commandArgs = append(commandArgs, ffmpegInputArgs...)

	if len(localInputFiles) > 1 {
		amixFilter := fmt.Sprintf("amix=inputs=%d:duration=longest", len(localInputFiles))
		commandArgs = append(commandArgs, "-filter_complex", amixFilter, tempOutputFile)
	} else if len(localInputFiles) == 1 { // Single input, just copy/re-encode
		commandArgs = append(commandArgs, "-c:a", "copy", tempOutputFile) // Attempt copy, FFMpeg will re-encode if necessary for container
		log.Println("Layering with single input: attempting codec copy. FFMpeg may re-encode if codec is incompatible with output container.")
	} else { // Should not happen due to earlier check
		return mcp.NewToolResultError("No input files for layering."), nil
	}

	_, ffmpegErr := runFFmpegCommand(ctx, commandArgs...) // from ffmpeg_commands.go
	if ffmpegErr != nil {
		// If -c copy failed for single file, try re-encoding to common AAC for MP3/M4A or PCM for WAV
		if len(localInputFiles) == 1 && strings.Contains(ffmpegErr.Error(), "could not find tag for codec") || strings.Contains(ffmpegErr.Error(), "does not support stream copying") {
			log.Printf("Codec copy failed for single file layering, attempting re-encode. Original error: %v", ffmpegErr)
			var reencodeArgs []string
			reencodeArgs = append(reencodeArgs, "-y", "-i", localInputFiles[0]) // Only one input
			if defaultOutputExt == "wav" {
				reencodeArgs = append(reencodeArgs, "-c:a", "pcm_s16le", tempOutputFile)
			} else { // Default to AAC for mp3, m4a etc.
				reencodeArgs = append(reencodeArgs, "-c:a", "aac", "-b:a", "192k", tempOutputFile)
			}
			_, ffmpegErr = runFFmpegCommand(ctx, reencodeArgs...)
		}
		if ffmpegErr != nil { // If still error after potential retry
			return mcp.NewToolResultError(fmt.Sprintf("FFMpeg audio layering failed: %v", ffmpegErr)), nil
		}
	}

	finalLocalPath, finalGCSPath, processErr := processOutputAfterFFmpeg(ctx, tempOutputFile, finalOutputFilename, outputLocalDir, outputGCSBucket) // from file_utils.go
	if processErr != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to process FFMpeg output: %v", processErr)), nil
	}

	duration := time.Since(startTime)
	var messageParts []string
	messageParts = append(messageParts, fmt.Sprintf("Audio layering of %d files completed in %v.", len(localInputFiles), duration))
	if outputLocalDir != "" && finalLocalPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output saved locally to: %s.", finalLocalPath))
	} else if finalLocalPath != "" && !(outputGCSBucket != "" && finalGCSPath != "") {
		messageParts = append(messageParts, fmt.Sprintf("Temporary output was at: %s (cleaned up if not moved/uploaded).", finalLocalPath))
	}
	if finalGCSPath != "" {
		messageParts = append(messageParts, fmt.Sprintf("Output uploaded to GCS: %s.", finalGCSPath))
	}
	if len(messageParts) == 1 {
		messageParts = append(messageParts, "No specific output location requested beyond temporary processing.")
	}
	return mcp.NewToolResultText(strings.Join(messageParts, " ")), nil
}

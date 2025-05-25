package main

import (
	"context"
	"errors"
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp" // For matching UID part of filename
	"strings"
	"testing"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
)

func TestParseGCSPath(t *testing.T) {
	tests := []struct {
		name         string
		gcsURI       string
		wantBucket   string
		wantObject   string
		wantErr      bool
		errContains  string // Substring to check in error message
	}{
		{
			name:       "valid path",
			gcsURI:     "gs://my-bucket/path/to/object.txt",
			wantBucket: "my-bucket",
			wantObject: "path/to/object.txt",
			wantErr:    false,
		},
		{
			name:       "valid path no prefix slashes in object",
			gcsURI:     "gs://my-bucket/object.txt",
			wantBucket: "my-bucket",
			wantObject: "object.txt",
			wantErr:    false,
		},
		{
			name:       "valid path with multiple slashes in object",
			gcsURI:     "gs://another-bucket/a/b/c/d/e.jpg",
			wantBucket: "another-bucket",
			wantObject: "a/b/c/d/e.jpg",
			wantErr:    false,
		},
		{
			name:        "invalid prefix",
			gcsURI:      "gcs://my-bucket/path/to/object.txt",
			wantErr:     true,
			errContains: "invalid GCS URI: must start with 'gs://'",
		},
		{
			name:        "missing gs prefix",
			gcsURI:      "my-bucket/path/to/object.txt",
			wantErr:     true,
			errContains: "invalid GCS URI: must start with 'gs://'",
		},
		{
			name:        "empty uri",
			gcsURI:      "",
			wantErr:     true,
			errContains: "invalid GCS URI: must start with 'gs://'",
		},
		{
			name:        "only gs prefix",
			gcsURI:      "gs://",
			wantErr:     true,
			errContains: "invalid GCS URI format",
		},
		{
			name:        "bucket name only",
			gcsURI:      "gs://my-bucket",
			wantErr:     true,
			errContains: "invalid GCS URI format",
		},
		{
			name:        "bucket name with trailing slash only",
			gcsURI:      "gs://my-bucket/", // This is tricky, SplitN behavior
			wantErr:     true,
			errContains: "invalid GCS URI format", // Expects object name part to be non-empty
		},
		{
			name:        "empty bucket name",
			gcsURI:      "gs:///path/to/object.txt",
			wantErr:     true,
			errContains: "invalid GCS URI format",
		},
		{
            name:       "object with spaces",
            gcsURI:     "gs://my-bucket/path with spaces/to object.txt",
            wantBucket: "my-bucket",
            wantObject: "path with spaces/to object.txt",
            wantErr:    false,
        },
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gotBucket, gotObject, err := parseGCSPath(tt.gcsURI)
			if (err != nil) != tt.wantErr {
				t.Errorf("parseGCSPath() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if err != nil && tt.errContains != "" {
				if !strings.Contains(err.Error(), tt.errContains) {
					t.Errorf("parseGCSPath() error = %v, want error containing %q", err, tt.errContains)
				}
			}
			if gotBucket != tt.wantBucket {
				t.Errorf("parseGCSPath() gotBucket = %v, want %v", gotBucket, tt.wantBucket)
			}
			if gotObject != tt.wantObject {
				t.Errorf("parseGCSPath() gotObject = %v, want %v", gotObject, tt.wantObject)
			}
		})
	}
}

func TestFfmpegVideoToGifHandler(t *testing.T) {
	tempVideoFile, err := os.CreateTemp(t.TempDir(), "test_video_gif_*.mp4")
	if err != nil {
		t.Fatalf("Failed to create temp video file for gif test: %v", err)
	}
	tempVideoFilePath := tempVideoFile.Name()
	tempVideoFile.Close()

	tests := []struct {
		name                   string
		requestArgs            map[string]interface{}
		setEnvVars             map[string]string
		mockFFmpegCalls        []struct { // To track expected args for multiple ffmpeg calls
			argsCheck func(t *testing.T, args []string)
			err       error
			output    string
		}
		mockPrepareVideoError  bool
		mockProcessOutputError error
		wantErr                bool
		wantErrMsgContains     string
		wantResultContains     []string
	}{
		{
			name: "valid local input, default scale/fps, local output",
			requestArgs: map[string]interface{}{
				"input_video_uri":  tempVideoFilePath,
				"output_local_dir": "gif_output_dir", // Will be scoped under t.TempDir()
				"output_file_name": "output.gif",
			},
			mockFFmpegCalls: []struct {
				argsCheck func(t *testing.T, args []string)
				err       error
				output    string
			}{
				{ // Palettegen call
					argsCheck: func(t *testing.T, args []string) {
						expectedVFFilter := "fps=15.00,scale=iw*0.33:-1:flags=lanczos+accurate_rnd+full_chroma_inp,palettegen"
						found := false
						for i, arg := range args {
							if arg == "-vf" && i+1 < len(args) && args[i+1] == expectedVFFilter { found = true; break }
						}
						if !found { t.Errorf("ffmpeg palettegen args %v incorrect, want vf filter %q", args, expectedVFFilter) }
						if !strings.HasSuffix(args[len(args)-1], "palette.png") {
							t.Errorf("ffmpeg palettegen output %s not palette.png", args[len(args)-1])
						}
					},
					err:    nil,
					output: "palettegen success",
				},
				{ // Paletteuse call
					argsCheck: func(t *testing.T, args []string) {
						expectedLavfiFilter := "fps=15.00,scale=iw*0.33:-1:flags=lanczos+accurate_rnd+full_chroma_inp [x]; [x][1:v] paletteuse"
						found := false
						for i, arg := range args {
							if arg == "-lavfi" && i+1 < len(args) && args[i+1] == expectedLavfiFilter { found = true; break }
						}
						if !found { t.Errorf("ffmpeg paletteuse args %v incorrect, want lavfi filter %q", args, expectedLavfiFilter) }
						if !strings.HasSuffix(args[len(args)-3], "palette.png") {
							t.Errorf("ffmpeg paletteuse input %s not palette.png", args[len(args)-3])
						}
						if !strings.HasSuffix(args[len(args)-1], "output.gif") {
							t.Errorf("ffmpeg paletteuse output %s not output.gif", args[len(args)-1])
						}
					},
					err:    nil,
					output: "paletteuse success",
				},
			},
			wantErr:            false,
			wantResultContains: []string{"GIF creation completed", "Output GIF saved locally to:", "gif_output_dir/output.gif"},
		},
		{
			name: "custom scale and fps",
			requestArgs: map[string]interface{}{
				"input_video_uri":  tempVideoFilePath,
				"scale_width_factor": float64(0.5),
				"fps":              float64(10),
				"output_file_name": "custom.gif",
			},
			mockFFmpegCalls: []struct {
				argsCheck func(t *testing.T, args []string)
				err       error
				output    string
			}{
				{ // Palettegen call
					argsCheck: func(t *testing.T, args []string) {
						expectedVFFilter := "fps=10.00,scale=iw*0.50:-1:flags=lanczos+accurate_rnd+full_chroma_inp,palettegen"
						if !containsArgWithValue(args, "-vf", expectedVFFilter) {
							t.Errorf("ffmpeg palettegen custom args %v incorrect, want vf filter %q", args, expectedVFFilter)
						}
					},
				},
				{ // Paletteuse call
					argsCheck: func(t *testing.T, args []string) {
						expectedLavfiFilter := "fps=10.00,scale=iw*0.50:-1:flags=lanczos+accurate_rnd+full_chroma_inp [x]; [x][1:v] paletteuse"
						if !containsArgWithValue(args, "-lavfi", expectedLavfiFilter) {
							t.Errorf("ffmpeg paletteuse custom args %v incorrect, want lavfi filter %q", args, expectedLavfiFilter)
						}
					},
				},
			},
			wantErr:            false,
			wantResultContains: []string{"GIF creation completed"},
		},
		{
			name: "missing input_video_uri",
			requestArgs: map[string]interface{}{
				"output_file_name": "output.gif",
			},
			wantErr:            true,
			wantErrMsgContains: "Parameter 'input_video_uri' is required",
		},
		{
			name: "palette generation fails",
			requestArgs: map[string]interface{}{
				"input_video_uri": tempVideoFilePath,
			},
			mockFFmpegCalls: []struct {
				argsCheck func(t *testing.T, args []string)
				err       error
				output    string
			}{
				{ err: errors.New("palettegen error") },
			},
			wantErr:            true,
			wantErrMsgContains: "FFMpeg palette generation failed: ffmpeg command failed: palettegen error",
		},
		{
			name: "gif creation fails",
			requestArgs: map[string]interface{}{
				"input_video_uri": tempVideoFilePath,
			},
			mockFFmpegCalls: []struct {
				argsCheck func(t *testing.T, args []string)
				err       error
				output    string
			}{
				{ output: "palettegen success" }, // First call succeeds
				{ err: errors.New("gif creation error") }, // Second call fails
			},
			wantErr:            true,
			wantErrMsgContains: "FFMpeg GIF creation failed: ffmpeg command failed: gif creation error",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			setupHandlerTests(t)
			defer teardownHandlerTests(t)

			for k, v := range tt.setEnvVars {
				t.Setenv(k, v)
			}
			if val, ok := tt.setEnvVars["GENMEDIA_BUCKET"]; ok {
				genmediaBucketEnv = val
			} else {
				genmediaBucketEnv = ""
			}
			
			currentRequestArgs := make(map[string]interface{})
			for k, v := range tt.requestArgs {
				currentRequestArgs[k] = v
			}
			if outputDir, ok := currentRequestArgs["output_local_dir"].(string); ok {
				absOutputDir := filepath.Join(t.TempDir(), outputDir)
				currentRequestArgs["output_local_dir"] = absOutputDir
			}

			ffmpegCallIndex := 0
			runFFmpegCommand = func(ctx context.Context, args ...string) (string, error) {
				if ffmpegCallIndex >= len(tt.mockFFmpegCalls) {
					t.Fatalf("Unexpected ffmpeg call (index %d). Expected %d calls.", ffmpegCallIndex, len(tt.mockFFmpegCalls))
				}
				callInfo := tt.mockFFmpegCalls[ffmpegCallIndex]
				if callInfo.argsCheck != nil {
					callInfo.argsCheck(t, args)
				}
				ffmpegCallIndex++
				return callInfo.output, callInfo.err
			}
			
			baseMockPrepareInputFile := prepareInputFile 
			prepareInputFile = func(ctx context.Context, fileURI, purpose string) (string, func(), error) {
				if purpose == "input_video_for_gif" && tt.mockPrepareVideoError { // Use specific purpose
					return "", func() {}, fmt.Errorf("mock file not found: %s", fileURI)
				}
				return baseMockPrepareInputFile(ctx, fileURI, purpose)
			}

			if tt.mockProcessOutputError != nil {
				processOutputAfterFFmpeg = func(ctx context.Context, ffmpegOutputActualPath, finalOutputFilename, outputLocalDir, outputGCSBucket string) (string, string, error) {
					return "", "", tt.mockProcessOutputError
				}
			}

			request := mcp.CallToolRequest{
				Params: mcp.ToolCallParams{Arguments: currentRequestArgs},
			}

			result, err := ffmpegVideoToGifHandler(context.Background(), request)

			if (err != nil) != tt.wantErr {
				t.Errorf("ffmpegVideoToGifHandler() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if err != nil {
				if tt.wantErrMsgContains != "" && !strings.Contains(err.Error(), tt.wantErrMsgContains) {
					t.Errorf("ffmpegVideoToGifHandler() error = %q, want error containing %q", err.Error(), tt.wantErrMsgContains)
				}
				return
			}

			if result == nil {
				t.Fatalf("ffmpegVideoToGifHandler() result is nil, expected non-nil result")
			}

			var resultText string
			for _, content := range result.Content {
				if textContent, ok := content.(mcp.TextContent); ok {
					resultText += textContent.Text + " "
				}
			}
			resultText = strings.TrimSpace(resultText)

			for _, wantSubstr := range tt.wantResultContains {
				if !strings.Contains(resultText, wantSubstr) {
					t.Errorf("ffmpegVideoToGifHandler() result text = %q, want to contain %q", resultText, wantSubstr)
				}
			}
		})
	}
}

// Helper function to check if a specific argument and its value are present
func containsArgWithValue(args []string, argName string, argValue string) bool {
	for i, arg := range args {
		if arg == argName && i+1 < len(args) && args[i+1] == argValue {
			return true
		}
	}
	return false
}

func TestFfmpegOverlayImageHandler(t *testing.T) {
	tempVideoFile, err := os.CreateTemp(t.TempDir(), "test_video_overlay_*.mp4")
	if err != nil {
		t.Fatalf("Failed to create temp video file for overlay: %v", err)
	}
	tempVideoFilePath := tempVideoFile.Name()
	tempVideoFile.Close()

	tempImageFile, err := os.CreateTemp(t.TempDir(), "test_image_overlay_*.png")
	if err != nil {
		t.Fatalf("Failed to create temp image file for overlay: %v", err)
	}
	tempImageFilePath := tempImageFile.Name()
	tempImageFile.Close()

	tests := []struct {
		name                   string
		requestArgs            map[string]interface{}
		setEnvVars             map[string]string
		mockFFmpegArgsCheck    func(t *testing.T, args []string) // For checking args passed to ffmpeg
		mockFFmpegError        error
		mockPrepareVideoError  bool 
		mockPrepareImageError  bool 
		mockProcessOutputError error
		wantErr                bool
		wantErrMsgContains     string
		wantResultContains     []string
	}{
		{
			name: "valid local inputs, default coords, local output",
			requestArgs: map[string]interface{}{
				"input_video_uri":  tempVideoFilePath,
				"input_image_uri":  tempImageFilePath,
				"output_local_dir": "overlay_output_dir", 
				"output_file_name": "overlayed.mp4",
				// x_coordinate and y_coordinate use default 0
			},
			mockFFmpegArgsCheck: func(t *testing.T, args []string) {
				expectedFilter := "[0:v][1:v]overlay=0:0"
				foundFilter := false
				for i, arg := range args {
					if arg == "-filter_complex" && i+1 < len(args) && args[i+1] == expectedFilter {
						foundFilter = true
						break
					}
				}
				if !foundFilter {
					t.Errorf("ffmpeg args %v did not contain expected overlay filter %q", args, expectedFilter)
				}
			},
			wantErr:            false,
			wantResultContains: []string{"Image overlay on video completed", "Output saved locally to:", "overlay_output_dir/overlayed.mp4"},
		},
		{
			name: "valid local inputs, custom coords",
			requestArgs: map[string]interface{}{
				"input_video_uri":  tempVideoFilePath,
				"input_image_uri":  tempImageFilePath,
				"x_coordinate":     float64(100), // MCP framework sends numbers as float64
				"y_coordinate":     float64(50),
				"output_file_name": "overlay_custom.mp4",
			},
			mockFFmpegArgsCheck: func(t *testing.T, args []string) {
				expectedFilter := "[0:v][1:v]overlay=100:50"
				foundFilter := false
				for i, arg := range args {
					if arg == "-filter_complex" && i+1 < len(args) && args[i+1] == expectedFilter {
						foundFilter = true
						break
					}
				}
				if !foundFilter {
					t.Errorf("ffmpeg args %v did not contain expected overlay filter %q", args, expectedFilter)
				}
			},
			wantErr:            false,
			wantResultContains: []string{"Image overlay on video completed"},
		},
		{
			name: "missing input_video_uri",
			requestArgs: map[string]interface{}{
				"input_image_uri": tempImageFilePath,
			},
			wantErr:            true,
			wantErrMsgContains: "Parameters 'input_video_uri' and 'input_image_uri' are required",
		},
		{
			name: "prepareInputFile fails for image",
			requestArgs: map[string]interface{}{
				"input_video_uri": tempVideoFilePath,
				"input_image_uri": "force_prepare_error.png",
			},
			mockPrepareImageError: true,
			wantErr:               true,
			wantErrMsgContains:    "Failed to prepare input image: mock file not found: force_prepare_error.png",
		},
		{
			name: "ffmpeg command fails",
			requestArgs: map[string]interface{}{
				"input_video_uri": tempVideoFilePath,
				"input_image_uri": tempImageFilePath,
			},
			mockFFmpegError:    errors.New("ffmpeg overlay error"),
			wantErr:            true,
			wantErrMsgContains: "FFMpeg overlay image failed: ffmpeg command failed: ffmpeg overlay error",
		},
		{
			name: "GENMEDIA_BUCKET default used for GCS output",
			requestArgs: map[string]interface{}{
				"input_video_uri": tempVideoFilePath,
				"input_image_uri": tempImageFilePath,
				// output_gcs_bucket is omitted
			},
			setEnvVars: map[string]string{
				"GENMEDIA_BUCKET": "default_overlay_bucket",
			},
			wantErr:            false,
			wantResultContains: []string{"Uploaded to GCS: gs://default_overlay_bucket/"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			setupHandlerTests(t)
			defer teardownHandlerTests(t)

			for k, v := range tt.setEnvVars {
				t.Setenv(k, v)
			}
			if val, ok := tt.setEnvVars["GENMEDIA_BUCKET"]; ok {
				genmediaBucketEnv = val
			} else {
				genmediaBucketEnv = ""
			}
			
			currentRequestArgs := make(map[string]interface{})
			for k, v := range tt.requestArgs {
				currentRequestArgs[k] = v
			}

			if outputDir, ok := currentRequestArgs["output_local_dir"].(string); ok {
				absOutputDir := filepath.Join(t.TempDir(), outputDir)
				currentRequestArgs["output_local_dir"] = absOutputDir
			}

			var capturedFFmpegArgs []string
			runFFmpegCommand = func(ctx context.Context, args ...string) (string, error) {
				capturedFFmpegArgs = args
				return "mock ffmpeg success", tt.mockFFmpegError
			}

			baseMockPrepareInputFile := prepareInputFile 
			prepareInputFile = func(ctx context.Context, fileURI, purpose string) (string, func(), error) {
				if purpose == "input_video" && tt.mockPrepareVideoError {
					return "", func() {}, fmt.Errorf("mock file not found: %s", fileURI)
				}
				if purpose == "input_image" && tt.mockPrepareImageError {
					return "", func() {}, fmt.Errorf("mock file not found: %s", fileURI)
				}
				return baseMockPrepareInputFile(ctx, fileURI, purpose)
			}
			
			if tt.mockProcessOutputError != nil {
				processOutputAfterFFmpeg = func(ctx context.Context, ffmpegOutputActualPath, finalOutputFilename, outputLocalDir, outputGCSBucket string) (string, string, error) {
					return "", "", tt.mockProcessOutputError
				}
			}

			request := mcp.CallToolRequest{
				Params: mcp.ToolCallParams{Arguments: currentRequestArgs},
			}

			result, err := ffmpegOverlayImageHandler(context.Background(), request)

			if tt.mockFFmpegArgsCheck != nil && tt.mockFFmpegError == nil {
				tt.mockFFmpegArgsCheck(t, capturedFFmpegArgs)
			}

			if (err != nil) != tt.wantErr {
				t.Errorf("ffmpegOverlayImageHandler() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if err != nil {
				if tt.wantErrMsgContains != "" && !strings.Contains(err.Error(), tt.wantErrMsgContains) {
					t.Errorf("ffmpegOverlayImageHandler() error = %q, want error containing %q", err.Error(), tt.wantErrMsgContains)
				}
				return
			}

			if result == nil {
				t.Fatalf("ffmpegOverlayImageHandler() result is nil, expected non-nil result")
			}

			var resultText string
			for _, content := range result.Content {
				if textContent, ok := content.(mcp.TextContent); ok {
					resultText += textContent.Text + " "
				}
			}
			resultText = strings.TrimSpace(resultText)

			for _, wantSubstr := range tt.wantResultContains {
				if !strings.Contains(resultText, wantSubstr) {
					t.Errorf("ffmpegOverlayImageHandler() result text = %q, want to contain %q", resultText, wantSubstr)
				}
			}
		})
	}
}

func TestHandleOutputPreparation(t *testing.T) {
	// Original shortid.Generate if we were to mock it. For now, we won't.
	// originalShortIDGenerate := shortid.Generate
	// defer func() { shortid.Generate = originalShortIDGenerate }()

	tests := []struct {
		name                  string
		desiredOutputFilename string
		defaultExt            string
		wantFinalNamePattern  string // Regexp pattern for final name if UID is involved
		wantFinalNameExact    string // Exact name if no UID is involved
		wantExt               string
		wantErr               bool
	}{
		{
			name:                  "empty desired name, mp3 default",
			desiredOutputFilename: "",
			defaultExt:            "mp3",
			wantFinalNamePattern:  `^ffmpeg_output_[\w-]{7,14}\.mp3$`, // shortid default length is variable
			wantExt:               ".mp3",
			wantErr:               false,
		},
		{
			name:                  "empty desired name, mp4 default",
			desiredOutputFilename: "",
			defaultExt:            "mp4",
			wantFinalNamePattern:  `^ffmpeg_output_[\w-]{7,14}\.mp4$`,
			wantExt:               ".mp4",
			wantErr:               false,
		},
		{
			name:                  "desired name with ext, mp4 default",
			desiredOutputFilename: "my_video.mp4",
			defaultExt:            "mp4",
			wantFinalNameExact:    "my_video.mp4",
			wantExt:               ".mp4",
			wantErr:               false,
		},
		{
			name:                  "desired name without ext, mp3 default",
			desiredOutputFilename: "my_audio",
			defaultExt:            "mp3",
			wantFinalNameExact:    "my_audio.mp3",
			wantExt:               ".mp3",
			wantErr:               false,
		},
		{
			name:                  "desired name with different ext, mp4 default",
			desiredOutputFilename: "my_clip.mov",
			defaultExt:            "mp4",
			wantFinalNameExact:    "my_clip.mov", // Should use original extension and log warning
			wantExt:               ".mov",
			wantErr:               false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// If we were to mock shortid.Generate for predictable UIDs:
			// shortid.Generate = func() (string, error) { return "testuid123", nil }

			tempLocalOutputFile, finalOutputFilename, cleanupFunc, err := handleOutputPreparation(tt.desiredOutputFilename, tt.defaultExt)
			defer cleanupFunc() // Ensure cleanup is always called

			if (err != nil) != tt.wantErr {
				t.Errorf("handleOutputPreparation() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if err != nil {
				// Further error content checks if needed
				return
			}

			// Check if tempLocalOutputFile is in a temporary directory
			// os.TempDir() might not be the exact parent if "" was used in MkdirTemp,
			// but it should be within some system-defined temp structure.
			// A simple check is that it's an absolute path and not the same as finalOutputFilename if final is simple.
			if !filepath.IsAbs(tempLocalOutputFile) {
				t.Errorf("handleOutputPreparation() tempLocalOutputFile = %v, want absolute path", tempLocalOutputFile)
			}
			if strings.Contains(tempLocalOutputFile, "..") { // Basic sanity check for path traversal
				t.Errorf("handleOutputPreparation() tempLocalOutputFile = %v, contains '..'", tempLocalOutputFile)
			}
			
			// Verify the directory of tempLocalOutputFile exists
			tempDir := filepath.Dir(tempLocalOutputFile)
			if _, statErr := os.Stat(tempDir); os.IsNotExist(statErr) {
				t.Errorf("handleOutputPreparation() temp directory %v does not exist", tempDir)
			}


			// Check finalOutputFilename
			if tt.wantFinalNameExact != "" {
				if finalOutputFilename != tt.wantFinalNameExact {
					t.Errorf("handleOutputPreparation() finalOutputFilename = %v, wantExact %v", finalOutputFilename, tt.wantFinalNameExact)
				}
			} else if tt.wantFinalNamePattern != "" {
				matched, _ := regexp.MatchString(tt.wantFinalNamePattern, finalOutputFilename)
				if !matched {
					t.Errorf("handleOutputPreparation() finalOutputFilename = %v, want pattern %v", finalOutputFilename, tt.wantFinalNamePattern)
				}
			}

			// Check extension of finalOutputFilename
			if ext := filepath.Ext(finalOutputFilename); ext != tt.wantExt {
				t.Errorf("handleOutputPreparation() finalOutputFilename extension = %v, want %v", ext, tt.wantExt)
			}
			
			// Check that tempLocalOutputFile contains the finalOutputFilename as its base
			if base := filepath.Base(tempLocalOutputFile); base != finalOutputFilename {
				t.Errorf("handleOutputPreparation() base of tempLocalOutputFile = %v, want %v (finalOutputFilename)", base, finalOutputFilename)
			}

			// Test cleanupFunc
			// First, ensure the temp directory exists
			if _, statErr := os.Stat(tempDir); os.IsNotExist(statErr) {
				t.Fatalf("handleOutputPreparation() temp directory %v did not exist before cleanup test", tempDir)
			}
			cleanupFunc() // Call the cleanup
			if _, statErr := os.Stat(tempDir); !os.IsNotExist(statErr) {
				t.Errorf("handleOutputPreparation() cleanupFunc did not remove temp directory %v", tempDir)
			}
		})
	}
}

func TestFfmpegCombineAudioVideoHandler(t *testing.T) {
	tempVideoFile, err := os.CreateTemp(t.TempDir(), "test_video_*.mp4")
	if err != nil {
		t.Fatalf("Failed to create temp video file: %v", err)
	}
	tempVideoFilePath := tempVideoFile.Name()
	tempVideoFile.Close()

	tempAudioFile, err := os.CreateTemp(t.TempDir(), "test_audio_*.wav")
	if err != nil {
		t.Fatalf("Failed to create temp audio file: %v", err)
	}
	tempAudioFilePath := tempAudioFile.Name()
	tempAudioFile.Close()

	tests := []struct {
		name                   string
		requestArgs            map[string]interface{}
		setEnvVars             map[string]string
		mockFFmpegArgsCheck    func(t *testing.T, args []string) // For checking args passed to ffmpeg
		mockFFmpegError        error
		mockPrepareVideoError  bool // True if prepareInputFile for video should fail
		mockPrepareAudioError  bool // True if prepareInputFile for audio should fail
		mockProcessOutputError error
		wantErr                bool
		wantErrMsgContains     string
		wantResultContains     []string
	}{
		{
			name: "valid local inputs, local output",
			requestArgs: map[string]interface{}{
				"input_video_uri":  tempVideoFilePath,
				"input_audio_uri":  tempAudioFilePath,
				"output_local_dir": "combined_output_dir", // Will be scoped under t.TempDir()
				"output_file_name": "combined.mp4",
			},
			wantErr:            false,
			wantResultContains: []string{"Audio and video combination completed", "Output saved locally to:", "combined_output_dir/combined.mp4"},
		},
		{
			name: "missing input_video_uri",
			requestArgs: map[string]interface{}{
				"input_audio_uri": tempAudioFilePath,
			},
			wantErr:            true,
			wantErrMsgContains: "Parameters 'input_video_uri' and 'input_audio_uri' are required",
		},
		{
			name: "missing input_audio_uri",
			requestArgs: map[string]interface{}{
				"input_video_uri": tempVideoFilePath,
			},
			wantErr:            true,
			wantErrMsgContains: "Parameters 'input_video_uri' and 'input_audio_uri' are required",
		},
		{
			name: "prepareInputFile fails for video",
			requestArgs: map[string]interface{}{
				"input_video_uri": "force_prepare_error.mp4",
				"input_audio_uri": tempAudioFilePath,
			},
			mockPrepareVideoError: true,
			wantErr:               true,
			wantErrMsgContains:    "Failed to prepare input video: mock file not found: force_prepare_error.mp4",
		},
		{
			name: "prepareInputFile fails for audio",
			requestArgs: map[string]interface{}{
				"input_video_uri": tempVideoFilePath,
				"input_audio_uri": "force_prepare_error.wav",
			},
			mockPrepareAudioError: true,
			wantErr:               true,
			wantErrMsgContains:    "Failed to prepare input audio: mock file not found: force_prepare_error.wav",
		},
		{
			name: "ffmpeg command fails",
			requestArgs: map[string]interface{}{
				"input_video_uri": tempVideoFilePath,
				"input_audio_uri": tempAudioFilePath,
			},
			mockFFmpegError:    errors.New("ffmpeg combine error"),
			wantErr:            true,
			wantErrMsgContains: "FFMpeg combine audio/video failed: ffmpeg command failed: ffmpeg combine error",
		},
		{
			name: "GENMEDIA_BUCKET default used for GCS output",
			requestArgs: map[string]interface{}{
				"input_video_uri": tempVideoFilePath,
				"input_audio_uri": tempAudioFilePath,
				// output_gcs_bucket is omitted
			},
			setEnvVars: map[string]string{
				"GENMEDIA_BUCKET": "default_combine_bucket",
			},
			wantErr:            false,
			wantResultContains: []string{"Uploaded to GCS: gs://default_combine_bucket/"},
		},
		{
			name: "check ffmpeg arguments",
			requestArgs: map[string]interface{}{
				"input_video_uri":  "gs://vid-bucket/input.mp4",
				"input_audio_uri":  "gs://aud-bucket/input.wav",
				"output_file_name": "custom_name.mp4",
			},
			mockFFmpegArgsCheck: func(t *testing.T, args []string) {
				if !strings.Contains(strings.Join(args, " "), filepath.Join(t.TempDir(), "input.mp4")) {
					t.Errorf("ffmpeg args %v do not contain expected video input %s", args, filepath.Join(t.TempDir(), "input.mp4"))
				}
				if !strings.Contains(strings.Join(args, " "), filepath.Join(t.TempDir(), "input.wav")) {
					t.Errorf("ffmpeg args %v do not contain expected audio input %s", args, filepath.Join(t.TempDir(), "input.wav"))
				}
				if !strings.Contains(strings.Join(args, " "), "custom_name.mp4") {
					t.Errorf("ffmpeg args %v do not contain expected output name %s", args, "custom_name.mp4")
				}
				expectedFlags := []string{"-map", "0", "-map", "1:a", "-c:v", "copy", "-shortest"}
				for _, flag := range expectedFlags {
					found := false
					for _, arg := range args {
						if arg == flag {
							found = true
							break
						}
					}
					if !found {
						t.Errorf("Expected ffmpeg flag %s not found in args: %v", flag, args)
					}
				}
			},
			wantErr: false,
			wantResultContains: []string{"Audio and video combination completed"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Store original functions and genmediaBucketEnv to restore them later
			setupHandlerTests(t)
			defer teardownHandlerTests(t)

			// Set environment variables for the test
			for k, v := range tt.setEnvVars {
				t.Setenv(k, v)
			}
			if val, ok := tt.setEnvVars["GENMEDIA_BUCKET"]; ok {
				genmediaBucketEnv = val
			} else {
				genmediaBucketEnv = "" 
			}
			
			currentRequestArgs := make(map[string]interface{})
			for k, v := range tt.requestArgs {
				currentRequestArgs[k] = v
			}

			if outputDir, ok := currentRequestArgs["output_local_dir"].(string); ok {
				absOutputDir := filepath.Join(t.TempDir(), outputDir)
				currentRequestArgs["output_local_dir"] = absOutputDir
			}

			// Customize mocks based on test case
			var capturedFFmpegArgs []string
			runFFmpegCommand = func(ctx context.Context, args ...string) (string, error) {
				capturedFFmpegArgs = args
				if tt.mockFFmpegArgsCheck != nil {
					// Allow test to panic if args are totally wrong, or use t.Error
				}
				return "mock ffmpeg success", tt.mockFFmpegError
			}

			// Refined mockPrepareInputFile for this test
			baseMockPrepareInputFile := prepareInputFile // The one set by setupHandlerTests
			prepareInputFile = func(ctx context.Context, fileURI, purpose string) (string, func(), error) {
				if purpose == "input_video" && tt.mockPrepareVideoError {
					return "", func() {}, fmt.Errorf("mock file not found: %s", fileURI)
				}
				if purpose == "input_audio" && tt.mockPrepareAudioError {
					return "", func() {}, fmt.Errorf("mock file not found: %s", fileURI)
				}
				// Fallback to the default mock behavior from setupHandlerTests
				return baseMockPrepareInputFile(ctx, fileURI, purpose)
			}
			
			if tt.mockProcessOutputError != nil {
				processOutputAfterFFmpeg = func(ctx context.Context, ffmpegOutputActualPath, finalOutputFilename, outputLocalDir, outputGCSBucket string) (string, string, error) {
					return "", "", tt.mockProcessOutputError
				}
			}

			request := mcp.CallToolRequest{
				Params: mcp.ToolCallParams{Arguments: currentRequestArgs},
			}

			result, err := ffmpegCombineAudioVideoHandler(context.Background(), request)

			if tt.mockFFmpegArgsCheck != nil && tt.mockFFmpegError == nil { // Only check args if ffmpeg was expected to be called and succeed
				tt.mockFFmpegArgsCheck(t, capturedFFmpegArgs)
			}

			if (err != nil) != tt.wantErr {
				t.Errorf("ffmpegCombineAudioVideoHandler() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if err != nil {
				if tt.wantErrMsgContains != "" && !strings.Contains(err.Error(), tt.wantErrMsgContains) {
					t.Errorf("ffmpegCombineAudioVideoHandler() error = %q, want error containing %q", err.Error(), tt.wantErrMsgContains)
				}
				return
			}

			if result == nil {
				t.Fatalf("ffmpegCombineAudioVideoHandler() result is nil, expected non-nil result")
			}

			var resultText string
			for _, content := range result.Content {
				if textContent, ok := content.(mcp.TextContent); ok {
					resultText += textContent.Text + " "
				}
			}
			resultText = strings.TrimSpace(resultText)

			for _, wantSubstr := range tt.wantResultContains {
				if !strings.Contains(resultText, wantSubstr) {
					t.Errorf("ffmpegCombineAudioVideoHandler() result text = %q, want to contain %q", resultText, wantSubstr)
				}
			}
		})
	}
}

func TestGetEnv(t *testing.T) {
	tests := []struct {
		name       string
		key        string
		setValue   string // Value to set for the env var, if any. Empty string means set but empty.
		isSet      bool   // Whether to set the env var at all.
		fallback   string
		want       string
		wantLog    bool   // Whether a log message about fallback is expected (not easily testable without capturing logs)
	}{
		{
			name:     "env var set",
			key:      "TEST_GETENV_SET",
			setValue: "my_value",
			isSet:    true,
			fallback: "fallback_value",
			want:     "my_value",
			wantLog:  false,
		},
		{
			name:     "env var not set",
			key:      "TEST_GETENV_NOT_SET",
			isSet:    false,
			fallback: "fallback_value",
			want:     "fallback_value",
			wantLog:  true,
		},
		{
			name:     "env var set to empty string",
			key:      "TEST_GETENV_EMPTY",
			setValue: "",
			isSet:    true,
			fallback: "fallback_value",
			want:     "fallback_value", // Behavior of the standardized getEnv
			wantLog:  true,
		},
		{
			name:     "fallback with special characters",
			key:      "TEST_GETENV_SPECIAL_FALLBACK",
			isSet:    false,
			fallback: "fallback with spaces & symbols!",
			want:     "fallback with spaces & symbols!",
			wantLog:  true,
		},
		{
			name:     "value with special characters",
			key:      "TEST_GETENV_SPECIAL_VALUE",
			setValue: "value with spaces & symbols!",
			isSet:    true,
			fallback: "fallback_value",
			want:     "value with spaces & symbols!",
			wantLog:  false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Clean up any env var that might have been set by a previous test case
			// or ensure it's not set if tt.isSet is false.
			t.Setenv(tt.key, "") // Effectively unsets or sets to empty for this test run's scope
			if tt.isSet {
				t.Setenv(tt.key, tt.setValue)
			} else {
				// To be absolutely sure it's not set from the parent environment for "not set" cases,
				// though t.Setenv(key, "") should generally cover it for the test's scope.
				// For this test, we assume t.Setenv handles making it appear "not set" if isSet is false
				// after the initial t.Setenv(tt.key, "").
			}

			// NOTE: Testing log output directly is complex and often requires redirecting log.SetOutput.
			// For this unit test, we'll focus on the functional correctness of getEnv (return value).
			// The `wantLog` field is more for documentation of expected behavior here.
			// If the `getEnv` function in `avtool.go` was updated to the standard version that logs,
			// then wantLog indicates when that log *should* occur.

			if got := getEnv(tt.key, tt.fallback); got != tt.want {
				t.Errorf("getEnv() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestGetTail(t *testing.T) {
	tests := []struct {
		name string
		s    string
		n    int
		want string
	}{
		{
			name: "n less than number of lines",
			s:    "line1
line2
line3
line4
line5",
			n:    3,
			want: "line3
line4
line5",
		},
		{
			name: "n equal to number of lines",
			s:    "line1
line2
line3",
			n:    3,
			want: "line1
line2
line3",
		},
		{
			name: "n greater than number of lines",
			s:    "line1
line2",
			n:    5,
			want: "line1
line2",
		},
		{
			name: "n is 0",
			s:    "line1
line2
line3",
			n:    0,
			want: "", // Or based on actual behavior, if n=0 means all lines or no lines. Current code implies last 0 lines.
		},
		{
			name: "n is 1",
			s:    "line1
line2
line3",
			n:    1,
			want: "line3",
		},
		{
			name: "empty string input",
			s:    "",
			n:    3,
			want: "",
		},
		{
			name: "single line input, n > 1",
			s:    "single line",
			n:    3,
			want: "single line",
		},
		{
			name: "single line input, n = 1",
			s:    "single line",
			n:    1,
			want: "single line",
		},
		{
			name: "string with trailing newline",
			s:    "line1
line2
line3
", // Trailing newline counts as an empty line by Split
			n:    2,
			want: "line3
", // The behavior of Split includes the empty string after the last 

		},
		{
			name: "string with only newlines",
			s:    "

",
			n:    2,
			want: "
", // Second to last and last "lines" which are empty string then 
 due to split
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := getTail(tt.s, tt.n); got != tt.want {
				t.Errorf("getTail() = %q, want %q", got, tt.want)
			}
		})
	}
}

// Mock implementations or variables for handler tests
var (
	originalRunFFmpegCommand        func(ctx context.Context, args ...string) (string, error)
	// mockRunFFmpegCommand is defined dynamically in tests or setup

	originalPrepareInputFile        func(ctx context.Context, fileURI, purpose string) (localPath string, cleanupFunc func(), err error)
	// mockPrepareInputFile is defined dynamically in tests or setup
	
	originalProcessOutputAfterFFmpeg func(ctx context.Context, ffmpegOutputActualPath, finalOutputFilename, outputLocalDir, outputGCSBucket string) (finalLocalPath string, finalGCSPath string, err error)
	// mockProcessOutputAfterFFmpeg is defined dynamically in tests or setup

	// This global variable is read by the handlers after being set by loadConfiguration (or getEnv in main).
	// Tests need to be able to manipulate this for simulating GENMEDIA_BUCKET effects.
	originalGenmediaBucketEnv string
)

// setupHandlerTests configures mocks for testing handlers.
// It should be called at the beginning of each relevant TestXxxHandler function.
func setupHandlerTests(t *testing.T) {
	originalRunFFmpegCommand = runFFmpegCommand
	originalPrepareInputFile = prepareInputFile
	originalProcessOutputAfterFFmpeg = processOutputAfterFFmpeg
	originalGenmediaBucketEnv = genmediaBucketEnv // Save the actual global state

	// Default mock behaviors (can be overridden in specific tests)
	runFFmpegCommand = func(ctx context.Context, args ...string) (string, error) {
		// t.Logf("mockRunFFmpegCommand called with args: %v", args)
		return "mock ffmpeg success", nil
	}
	
	dummyInputFile, err := os.CreateTemp(t.TempDir(), "test_dummy_input_*.wav")
	if err != nil {
		t.Fatalf("Failed to create dummy input file for tests: %v", err)
	}
	dummyInputFilePath := dummyInputFile.Name()
	dummyInputFile.Close()

	prepareInputFile = func(ctx context.Context, fileURI, purpose string) (string, func(), error) {
		// t.Logf("mockPrepareInputFile called with fileURI: %s, purpose: %s", fileURI, purpose)
		if strings.HasPrefix(fileURI, "gs://") {
			mockGCSDownloadPath := filepath.Join(t.TempDir(), filepath.Base(fileURI))
			// Simulate creating this file as if it were downloaded
			if _, err := os.Create(mockGCSDownloadPath); err != nil {
				t.Logf("mockPrepareInputFile: failed to create mock GCS download file %s: %v", mockGCSDownloadPath, err)
			}
			return mockGCSDownloadPath, func() { os.Remove(mockGCSDownloadPath) }, nil
		}
		if _, err := os.Stat(fileURI); err == nil { // Check if local file exists
			return fileURI, func() {}, nil
		}
		// Specific case for testing prepareInputFile failure if file doesn't exist
		if fileURI == "nonexistent.wav" || fileURI == "force_prepare_error.wav" {
		    return "", func() {}, fmt.Errorf("mock file not found: %s", fileURI)
		}
		// Fallback for other local file URI, assume it's the dummy one if it doesn't exist
		return dummyInputFilePath, func() {}, nil
	}

	processOutputAfterFFmpeg = func(ctx context.Context, ffmpegOutputActualPath, finalOutputFilename, outputLocalDir, outputGCSBucket string) (string, string, error) {
		// t.Logf("mockProcessOutputAfterFFmpeg called with actualPath: %s, finalName: %s, localDir: %s, gcsBucket: %s", ffmpegOutputActualPath, finalOutputFilename, outputLocalDir, outputGCSBucket)
		finalLocal := ""
		if outputLocalDir != "" {
			finalLocal = filepath.Join(outputLocalDir, finalOutputFilename)
			// Simulate creating the directory if it's part of the test's temp space
			if strings.HasPrefix(outputLocalDir, t.TempDir()) {
				if err := os.MkdirAll(filepath.Dir(finalLocal), 0755); err != nil {
					t.Logf("mockProcessOutputAfterFFmpeg: failed to MkdirAll for %s: %v", finalLocal, err)
				}
			}
		}
		finalGCS := ""
		if outputGCSBucket != "" {
			finalGCS = "gs://" + outputGCSBucket + "/" + finalOutputFilename
		}
		return finalLocal, finalGCS, nil
	}
}

// teardownHandlerTests restores original functions.
// It should be deferred after setupHandlerTests.
func teardownHandlerTests(t *testing.T) {
	runFFmpegCommand = originalRunFFmpegCommand
	prepareInputFile = originalPrepareInputFile
	processOutputAfterFFmpeg = originalProcessOutputAfterFFmpeg
	genmediaBucketEnv = originalGenmediaBucketEnv // Restore actual global state
}

func TestFfmpegConvertAudioHandler(t *testing.T) {
	tempInputFile, err := os.CreateTemp(t.TempDir(), "test_input_*.wav")
	if err != nil {
		t.Fatalf("Failed to create temp input file: %v", err)
	}
	tempInputFilePath := tempInputFile.Name()
	tempInputFile.Close()

	tests := []struct {
		name                   string
		requestArgs            map[string]interface{}
		setEnvVars             map[string]string 
		mockFFmpegResult       string
		mockFFmpegError        error
		mockPrepareError       bool // True if prepareInputFile should be forced to error
		mockProcessOutputError error
		wantErr                bool
		wantErrMsgContains     string
		wantResultContains     []string
	}{
		{
			name: "valid local input, local output",
			requestArgs: map[string]interface{}{
				"input_audio_uri":  tempInputFilePath,
				"output_local_dir": "test_output_dir", // Will be scoped under t.TempDir()
				"output_file_name": "converted.mp3",
			},
			wantErr:            false,
			wantResultContains: []string{"Audio conversion to MP3 completed", "Output saved locally to:", "test_output_dir/converted.mp3"},
		},
		{
			name: "missing input_audio_uri",
			requestArgs: map[string]interface{}{
				"output_local_dir": "test_output_dir",
			},
			wantErr:            true,
			wantErrMsgContains: "Parameter 'input_audio_uri' is required",
		},
		{
			name: "prepareInputFile fails",
			requestArgs: map[string]interface{}{
				"input_audio_uri": "force_prepare_error.wav", // Mock will make this fail
			},
			mockPrepareError:   true, 
			wantErr:            true,
			wantErrMsgContains: "Failed to prepare input audio: mock file not found: force_prepare_error.wav",
		},
		{
			name: "ffmpeg command fails",
			requestArgs: map[string]interface{}{
				"input_audio_uri": tempInputFilePath,
			},
			mockFFmpegError:    errors.New("ffmpeg simulated error"),
			wantErr:            true,
			wantErrMsgContains: "FFMpeg conversion failed: ffmpeg command failed: ffmpeg simulated error",
		},
		{
			name: "GENMEDIA_BUCKET default used",
			requestArgs: map[string]interface{}{
				"input_audio_uri": tempInputFilePath,
			},
			setEnvVars: map[string]string{
				"GENMEDIA_BUCKET": "env_default_bucket",
			},
			wantErr:            false,
			wantResultContains: []string{"Uploaded to GCS: gs://env_default_bucket/"},
		},
		{
			name: "Valid GCS input, local output",
			requestArgs: map[string]interface{}{
				"input_audio_uri":  "gs://test-bucket/input.wav",
				"output_local_dir": "local_out_gcs", // Will be scoped under t.TempDir()
				"output_file_name": "from_gcs.mp3",
			},
			wantErr: false,
			wantResultContains: []string{"Output saved locally to:", "local_out_gcs/from_gcs.mp3"},
		},
		{
			name: "processOutputAfterFFmpeg fails",
			requestArgs: map[string]interface{}{
				"input_audio_uri":  tempInputFilePath,
				"output_local_dir": "some_dir",
			},
			mockProcessOutputError: errors.New("simulated process output error"),
			wantErr:                true,
			wantErrMsgContains:     "Failed to process FFMpeg output: simulated process output error",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			setupHandlerTests(t)
			defer teardownHandlerTests(t)

			for k, v := range tt.setEnvVars {
				t.Setenv(k, v) // Go 1.17+ feature
			}
			// This is tricky: genmediaBucketEnv is set during loadConfiguration once.
			// For tests, we need to simulate it being set as if loadConfiguration ran with the env var.
			if val, ok := tt.setEnvVars["GENMEDIA_BUCKET"]; ok {
				genmediaBucketEnv = val
			} else {
				genmediaBucketEnv = "" // Ensure it's reset if not specified for this test
			}
			
			currentRequestArgs := make(map[string]interface{})
			for k, v := range tt.requestArgs {
				currentRequestArgs[k] = v
			}

			// Adjust output_local_dir to be inside t.TempDir() to avoid file system permission issues
			// and ensure cleanup.
			if outputDir, ok := currentRequestArgs["output_local_dir"].(string); ok {
				absOutputDir := filepath.Join(t.TempDir(), outputDir)
				// No need to MkdirAll here, processOutputAfterFFmpeg or its mock should handle it if needed
				currentRequestArgs["output_local_dir"] = absOutputDir
			}


			// Override default mocks based on test case specifics
			if tt.mockFFmpegError != nil || tt.mockFFmpegResult != "" {
				runFFmpegCommand = func(ctx context.Context, args ...string) (string, error) {
					return tt.mockFFmpegResult, tt.mockFFmpegError
				}
			}
			if tt.mockPrepareError { // Updated this condition
				// The mockPrepareInputFile is already set up to error on "force_prepare_error.wav"
				// If a different error is needed, re-assign prepareInputFile here:
				// prepareInputFile = func(...) (string, func(), error) { return "", func(){}, errors.New("specific prepare error") }
			}
			if tt.mockProcessOutputError != nil {
				processOutputAfterFFmpeg = func(ctx context.Context, ffmpegOutputActualPath, finalOutputFilename, outputLocalDir, outputGCSBucket string) (string, string, error) {
					return "", "", tt.mockProcessOutputError
				}
			}
			
			request := mcp.CallToolRequest{
				// ToolName: "ffmpeg_convert_audio_wav_to_mp3", // Not strictly needed by handler itself
				Params: mcp.ToolCallParams{Arguments: currentRequestArgs},
			}

			result, err := ffmpegConvertAudioHandler(context.Background(), request)

			if (err != nil) != tt.wantErr {
				t.Errorf("ffmpegConvertAudioHandler() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if err != nil {
				if tt.wantErrMsgContains != "" && !strings.Contains(err.Error(), tt.wantErrMsgContains) {
					t.Errorf("ffmpegConvertAudioHandler() error = %q, want error containing %q", err.Error(), tt.wantErrMsgContains)
				}
				return 
			}
			
			if result == nil {
				t.Fatalf("ffmpegConvertAudioHandler() result is nil, expected non-nil result")
			}
			
			var resultText string
            for _, content := range result.Content {
                if textContent, ok := content.(mcp.TextContent); ok {
                    resultText += textContent.Text + " "
                }
            }
            resultText = strings.TrimSpace(resultText)

			for _, wantSubstr := range tt.wantResultContains {
				if !strings.Contains(resultText, wantSubstr) {
					t.Errorf("ffmpegConvertAudioHandler() result text = %q, want to contain %q", resultText, wantSubstr)
				}
			}
		})
	}
}

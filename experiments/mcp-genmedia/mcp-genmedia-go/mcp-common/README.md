# MCP Common

This package provides common functionality for the MCP services in this repository.

## Configuration

The `config.go` file provides a way to load configuration from environment variables. The `LoadConfig` function returns a `Config` struct that contains the following fields:

* `ProjectID`: The Google Cloud project ID.
* `Location`: The Google Cloud location.
* `GenmediaBucket`: The Google Cloud Storage bucket for general media.
* `LyriaLocation`: The Google Cloud location for Lyria.
* `LyriaModelPublisher`: The model publisher for Lyria.
* `DefaultLyriaModelID`: The default model ID for Lyria.

The `GetEnv` function is a helper function that gets an environment variable or returns a fallback value if the environment variable is not set.

## File Utilities

The `file_utils.go` file provides utility functions for working with files. The following functions are provided:

* `PrepareInputFile`: This function prepares an input file for processing. It can handle both local files and files in Google Cloud Storage. If the file is in Google Cloud Storage, it will be downloaded to a temporary local file. The function returns the path to the local file and a cleanup function that should be called to remove the temporary file.
* `HandleOutputPreparation`: This function prepares for writing an output file. It creates a temporary local file and returns the path to the file, the final output filename, and a cleanup function.
* `ProcessOutputAfterFFmpeg`: This function processes the output of an FFmpeg command. It can move the output file to a specified local directory and/or upload it to Google Cloud Storage.
* `GetTail`: This function returns the last n lines of a string.
* `FormatBytes`: This function formats a size in bytes to a human-readable string (KB, MB, GB).

## GCS Utilities

The `gcs_utils.go` file provides utility functions for working with Google Cloud Storage. The following functions are provided:

* `DownloadFromGCS`: This function downloads a file from Google Cloud Storage to a local file.
* `UploadToGCS`: This function uploads a file to Google Cloud Storage.
* `ParseGCSPath`: This function parses a Google Cloud Storage URI and returns the bucket name and object name.

## OpenTelemetry

The `otel.go` file provides a function for initializing OpenTelemetry. The `InitTracerProvider` function initializes a tracer provider and returns it. The tracer provider can be used to create tracers and spans.

## Testing

To test the `mcp-common` package, run the following command from the `mcp-common` directory:

```
go test
```
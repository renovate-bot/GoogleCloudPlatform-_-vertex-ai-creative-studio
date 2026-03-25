# Changelog

## 2026-03-25 (v3.1.2)

*   **Fix:** Updated the `mcp-nanobanana-go` and `mcp-gemini-go` servers to natively handle image generation `aspect_ratio` constraints using the `ImageConfig` field rather than prompt injection, causing the API to accurately reject invalid aspect ratios like `"auto"`.
*   **Fix:** Resolved a bash syntax error in `install-online.sh` that broke the installer when piped directly from `curl` into `bash`.
*   **Fix:** Corrected an architecture mapping bug in `install-online.sh` that caused `amd64` Linux and Windows users to receive a 404 error when downloading the release binaries.
*   **Fix:** Configured GoReleaser to properly bundle the Antigravity agent configurations (`mcp_config.json` and `SKILL.md`) inside the `.tar.gz` release archives, enabling the interactive Antigravity installation prompt to function correctly.

## 2026-03-25 (v3.1.1)

*   **Fix:** Resolved a routing issue where Lyria 3 models were inadvertently hitting the legacy Prediction API instead of the new Interactions API.
*   **Fix:** Enforced `global` region strictly for the Lyria 3 Interactions API to prevent `NotFound` errors when `us-central1` is used as a fallback.
*   **Feat:** Added native support for the [Antigravity](https://antigravity.google) AI editor.
*   **Feat:** The `install-online.sh` and `install.sh` scripts now interactively offer to install the expert `genmedia-producer` Agent Skill globally for Antigravity.
*   **Docs:** Provided an Antigravity `mcp_config.json` template and instructions for connecting the GenMedia MCP suite.

## 2026-03-25 (v3.1.0)

*   **Feat:** Added support for `lyria-3-clip-preview` (30s) and `lyria-3-pro-preview` (2:30s) music generation models to `mcp-lyria-go`.
*   **Feat:** Implemented a new, lightweight Go port of the Vertex AI Interactions API to support the Lyria 3 backends.
*   **Feat:** Set `lyria-3-clip-preview` as the new default model for the `lyria_generate_music` tool.
*   **Config:** Added the Lyria model registry to `mcp-common/models.go` to provide self-describing model options to the LLM agent via the MCP tool description.

## 2026-03-24

*   **Feat:** Added a new `mcp-nanobanana-go` server dedicated to Google Gemini Image models.
*   **Feat:** Added `gemini-3.1-flash-image-preview` (Nano Banana 2) support to `mcp-gemini-go` and `mcp-nanobanana-go`, setting it as the new default model.
*   **Feat:** Added `SupportedAspectRatios` to Gemini Image model definitions and updated `mcp-gemini-go` and `mcp-nanobanana-go` to accept an `aspect_ratio` parameter.
*   **Feat:** Set `veo-3.1-fast-generate-001` as the new default model for `mcp-veo-go`.
*   **Deprecation:** Removed deprecated Veo models (`veo-2.0-generate-exp`, `veo-2.0-generate-preview`, `veo-3.0-generate-preview`, `veo-3.0-fast-generate-preview`, `veo-3.1-generate-preview`, `veo-3.1-fast-generate-preview`) from supported lists.
*   **Deprecation:** Excluded `mcp-imagen-go` from the standard `install.sh` installation loop (Imagen models set to be deprecated by June 30, 2026).
*   **Chore:** Updated Go GenAI SDK (`google.golang.org/genai`) from `v1.22.0` to `v1.51.0` and bumped all other module dependencies to latest versions.
*   **Fix:** Resolved numerous `golangci-lint` issues (errcheck, unused variables, string formatting) across all modules to ensure zero linting warnings.
*   **CI:** Added `.golangci.yml` configuration and a dedicated GitHub Actions workflow (`mcp-genmedia-go.yml`) for linting, building, and verifying tests for the MCP servers on PRs/pushes.
*   **Refactor:** Centralized OpenTelemetry initialization and configuration loading into a unified `common.Init` function in `mcp-common`.
*   **Docs:** Added a PATH reminder output to `install.sh` upon successful server installation.


## 2025-11-23

*   **Feat:** Added support for `gemini-3-pro-image-preview` (alias: "Nano Banana Pro") and `gemini-2.5-flash-image` (alias: "Nano Banana") to the `gemini_image_generation` tool in `mcp-gemini-go`.
*   **Feat:** Added `gemini-2.5-flash-lite-preview-tts` to the supported models in the `gemini_audio_tts` tool in `mcp-gemini-go`.
*   **Refactor:** Centralized Gemini Image model definitions in `mcp-common/models.go`, matching the architectural pattern used for Imagen and Veo.
*   **Chore:** Incremented `mcp-gemini-go` version to 0.5.1.

## 2025-10-09

*   **Feat:** Standardized network port configuration across all MCP servers (`avtool`, `chirp3`, `imagen`, `lyria`, `veo`, `gemini`). All servers now follow a consistent precedence: `--port` flag, `PORT` environment variable, and then transport-specific defaults (`8080` for `http`, `8081` for `sse`).
*   **Feat:** Added full HTTP transport support to the `mcp-gemini-go` server, making it accessible via HTTP in addition to `stdio`.
*   **Fix:** Corrected the port configuration logic in `mcp-avtool-go` to align with the new standard, including support for the `-p` short flag and a centralized `determinePort` function.
*   **Chore:** Incremented the version number for all MCP servers.

## 2025-10-01

*   **Feat:** Disabled OpenTelemetry tracing by default across all MCP servers. It can be re-enabled by setting the `OTEL_ENABLED=true` environment variable.
*   **Fix:** Removed the unused `-otel` command-line flag from the `mcp-veo-go` server.
*   **Test:** Added `verify.sh` scripts to `mcp-chirp3-go`, `mcp-avtool-go`, and `mcp-lyria-go` to provide a consistent, post-build liveness check.
*   **Chore:** Incremented the version number for all MCP servers.

## 2025-08-31

*   **Feat:** Added `gemini_audio_tts` and `list_gemini_voices` tools to the `mcp-gemini-go` server to provide speech synthesis capabilities using Gemini TTS models.
*   **Feat:** The new tools support all 30 voices available in the Gemini TTS documentation.
*   **Feat:** Added a `gemini://language_codes` resource to the `mcp-gemini-go` server to list supported languages.
*   **Docs:** Updated the `mcp-gemini-go/README.md` with documentation and usage examples for the new TTS tools and resource.

## 2025-08-29

*   **Feat:** Added a new `mcp-gemini-go` server to provide an MCP interface for Google's Gemini models.
*   **Feat:** The new server includes a `gemini_image_generation` tool for multimodal (text and image) content generation.
*   **Fix:** Resolved multiple build and dependency issues in the new server, including correcting Go module versions and fixing compilation errors.
*   **Docs:** Updated the main project `README.md` to include the `mcp-gemini-go` server in the installation instructions and the list of available servers.
*   **Chore:** Improved the `install.sh` script to verify that the `PROJECT_ID` environment variable is set, preventing a common installation failure.

## 2025-08-14

*   **Feat:** The `mcp-veo-go` tool now generates descriptive, unique filenames for downloaded videos (e.g., `veo-veo-2.0-generate-001-20250814-153000-0.mp4`), matching the behavior of the Imagen tool.
*   **Fix:** The `mcp-veo-go` tool now automatically prepends `gs://` to the GCS bucket name if it is missing, preventing an "Unsupported output storage uri" error.
*   **Feat:** Added a new `EnsureGCSPathPrefix` helper function to `mcp-common` to provide a consistent way to normalize GCS paths.
*   **Chore:** Incremented the version number for `mcp-veo-go`.
*   **Fix:** Improved logging in `mcp-common` to clarify fallback behavior for environment variables.
*   **Feat:** Updated Imagen 4 model names to production versions.
*   **Chore:** Incremented the version number for `mcp-imagen-go`.

## 2025-07-31

*   **Feat:** Added prompt support to all MCP servers to eliminate the `prompts not supported` error.
*   **Feat:** Implemented a `list-voices` prompt in `mcp-chirp3-go` that lists available voices and can be filtered by language.
*   **Feat:** Added a `chirp://language_codes` resource to `mcp-chirp3-go` to expose the supported language codes.
*   **Feat:** Implemented a `generate-image` prompt in `mcp-imagen-go` that wraps the `imagen_t2i` tool.
*   **Feat:** Implemented a `generate-video` prompt in `mcp-veo-go` that wraps the `veo_t2v` tool.
*   **Feat:** Implemented a `generate-music` prompt in `mcp-lyria-go` that wraps the `lyria_generate_music` tool.
*   **Feat:** Implemented a `create-gif` prompt in `mcp-avtool-go` that wraps the `ffmpeg_video_to_gif` tool.
*   **Refactor:** Refactored the voice listing logic in `mcp-chirp3-go` into a reusable helper function.
*   **Chore:** Incremented the version number for all MCP servers.

## 2025-07-19

*   **Feat:** Implemented dynamic, model-specific constraints for `mcp-imagen-go` and `mcp-veo-go`. This includes support for model aliases (e.g., "Imagen 4", "Veo 3") and validation of parameters like image count, video duration, and aspect ratios based on the selected model.
*   **Refactor:** Centralized all model definitions and constraints for both Imagen and Veo into a new `mcp-common/models.go` file. This creates a single source of truth and simplifies future maintenance.
*   **Fix:** Restored the server startup logic in `mcp-imagen-go` to prevent the server from exiting prematurely.
*   **Refactor:** Updated `mcp-imagen-go` and `mcp-veo-go` to use the new centralized model configuration.
*   **Docs:** Updated the tool descriptions for `mcp-imagen-go` and `mcp-veo-go` to be self-describing, dynamically listing all supported models and their constraints.
*   **Docs:** Updated the `README.md` files for `mcp-imagen-go` and `mcp-veo-go` to refer to the new `mcp-common/models.go` file as the single source of truth.
*   **Docs:** Added a new "Architectural Pattern" section to the `GEMINI.md` file to document the new configuration-driven approach for model constraints.
*   **Docs:** Added detailed instructions for testing MCP servers with `mcptools` to the project's `GEMINI.md`.
*   **Test:** Added `verify.sh` scripts to `mcp-imagen-go` and `mcp-veo-go` to provide a mandatory, post-build liveness check.

## 2025-06-10

*   **Docs:** Added comprehensive Go documentation to all public functions and methods in the `mcp-avtool-go`, `mcp-chirp3-go`, `mcp-common`, `mcp-imagen-go`, `mcp-lyria-go`, and `mcp-veo-go` packages to improve code clarity and maintainability.

## 2025-06-07

*   **Refactor:** Simplified the shared `mcp-common` configuration by removing redundant and service-specific fields (`LyriaLocation`, `LyriaModelPublisher`, `DefaultLyriaModelID`).
*   **Refactor:** Updated `mcp-lyria-go` to use the general `Location` and manage its own constants for model publisher and ID, decoupling it from the shared config.
*   **Fix:** Removed incorrect and unreachable error handling for `common.LoadConfig()` from `veo-go`, `mcp-imagen-go`, and `mcp-lyria-go`.
*   **Feat:** Added support for custom API endpoints in `mcp-imagen-go` and `veo-go` via the `VERTEX_API_ENDPOINT` environment variable. This allows for easier testing against preview or sandbox environments.
*   **Fix:** Resolved build errors in all MCP modules.
*   **Refactor:** Refactored `mcp-avtool-go`, `mcp-imagen-go`, `mcp-lyria-go`, and `veo-go` to use the shared `mcp-common` module.
*   **Feat:** Instrumented `mcp-avtool-go`, `mcp-imagen-go`, `mcp-lyria-go`, and `veo-go` with OpenTelemetry for tracing.
*   **Fix:** Resolved `go mod tidy` dependency issues in `mcp-avtool-go` and `mcp-imagen-go`.
*   **Fix:** Corrected errors in `mcp-chirp3-go` and refactored to use the `mcp-common` package.
*   **Docs:** Added a `README.md` to the `mcp-common` package.
*   **Docs:** Updated the `README.md` in `mcp-avtool-go` to reflect the current capabilities of the service.
*   **Docs:** Added `compositing_recipes.md` to `mcp-avtool-go` to document the `ffmpeg` and `ffprobe` commands used.
*   **Docs:** Updated the root `README.md` with a "Developing MCP Servers for Genmedia" section.

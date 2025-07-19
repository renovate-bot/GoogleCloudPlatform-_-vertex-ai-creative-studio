# Changelog

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

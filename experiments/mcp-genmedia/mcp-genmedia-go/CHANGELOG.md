# Changelog

## 2025-06-10

*   **Docs:** Added comprehensive Go documentation to all public functions and methods in the `mcp-avtool-go`, `mcp-chirp3-go`, `mcp-common`, `mcp-imagen-go`, `mcp-lyria-go`, and `mcp-veo-go` packages to improve code clarity and maintainability.

## 2025-06-07 (Afternoon)

*   **Refactor:** Simplified the shared `mcp-common` configuration by removing redundant and service-specific fields (`LyriaLocation`, `LyriaModelPublisher`, `DefaultLyriaModelID`).
*   **Refactor:** Updated `mcp-lyria-go` to use the general `Location` and manage its own constants for model publisher and ID, decoupling it from the shared config.
*   **Fix:** Removed incorrect and unreachable error handling for `common.LoadConfig()` from `mcp-veo-go`, `mcp-imagen-go`, and `mcp-lyria-go`.
*   **Feat:** Added support for custom API endpoints in `mcp-imagen-go` and `mcp-veo-go` via the `VERTEX_API_ENDPOINT` environment variable. This allows for easier testing against preview or sandbox environments.

## 2025-06-07

*   **Fix:** Resolved build errors in all MCP modules.
*   **Refactor:** Refactored `mcp-avtool-go`, `mcp-imagen-go`, `mcp-lyria-go`, and `mcp-veo-go` to use the shared `mcp-common` module.
*   **Feat:** Instrumented `mcp-avtool-go`, `mcp-imagen-go`, `mcp-lyria-go`, and `mcp-veo-go` with OpenTelemetry for tracing.
*   **Fix:** Resolved `go mod tidy` dependency issues in `mcp-avtool-go` and `mcp-imagen-go`.
*   **Fix:** Corrected errors in `mcp-chirp3-go` and refactored to use the `mcp-common` package.
*   **Docs:** Added a `README.md` to the `mcp-common` package.
*   **Docs:** Updated the `README.md` in `mcp-avtool-go` to reflect the current capabilities of the service.
*   **Docs:** Added `compositing_recipes.md` to `mcp-avtool-go` to document the `ffmpeg` and `ffprobe` commands used.
*   **Docs:** Updated the root `README.md` with a "Developing MCP Servers for Genmedia" section.

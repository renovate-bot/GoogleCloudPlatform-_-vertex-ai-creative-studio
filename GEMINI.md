---

## 7. Documentation Workflows

### Updating Documentation for New Features/Experiments

When new code, features, or experiments are added, it's crucial to update the relevant documentation to ensure discoverability and maintainability.

1.  **Identify Relevant Docs:** Determine which documentation files need updating (e.g., main `README.md`, `experiments/README.md`, `developers_guide.md`).
2.  **Analyze Existing Conventions:** Read the target documentation to understand its structure, tone, and formatting conventions for similar items.
3.  **Synthesize New Content:** Extract key information from the new feature's source code or its own README to create a concise and accurate description.
4.  **Propose Changes:** Present the proposed documentation changes to the user for review and approval before applying them. Use markdown blocks to clearly show the additions or modifications.
5.  **Apply Changes:** Use the `replace` or `write_file` tool to apply the approved changes.

## Go Modules & CI Environments

**golangci-lint in go.work Monorepos:**
When configuring `golangci-lint` to run in a CI environment (like GitHub Actions) across a multi-module `go.work` repository that uses local `replace` directives (e.g., `replace github.com/.../mcp-common => ../mcp-common`), do **not** use the official `golangci/golangci-lint-action` at the root. The GitHub runner filesystem boundaries will cause the Go typechecker to fail with `context loading failed: no go files to analyze`.

Instead, you MUST:
1. Physically delete `go.work` and `go.work.sum` in the CI pipeline before linting so Go treats the modules as fully isolated.
2. Manually install `golangci-lint` via curl.
3. Run the linter in a bash loop, explicitly changing directories into each submodule (`cd $dir && golangci-lint run ./...`).

**CI Verification Scripts (mcptools):**
If a Go application initializes network-dependent clients (like Google Cloud `genai.NewClient` or `texttospeech.NewClient`) on startup, it will hang indefinitely inside headless CI runners that lack ADC (Application Default Credentials). To allow tools like `mcptools` to verify the STDIO handshake in CI, you MUST make global client initialization non-fatal during `main()` and defer the strict credential check until the client is actually invoked inside the tool handler.

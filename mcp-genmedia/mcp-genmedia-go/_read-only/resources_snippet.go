// Static resource example - exposing a README file
resource := mcp.NewResource(
    "docs://readme",
    "Project README",
    mcp.WithResourceDescription("The project's README file"), 
    mcp.WithMIMEType("text/markdown"),
)

// Add resource with its handler
s.AddResource(resource, func(ctx context.Context, request mcp.ReadResourceRequest) ([]mcp.ResourceContents, error) {
    content, err := os.ReadFile("README.md")
    if err != nil {
        return nil, err
    }
    
    return []mcp.ResourceContents{
        mcp.TextResourceContents{
            URI:      "docs://readme",
            MIMEType: "text/markdown",
            Text:     string(content),
        },
    }, nil
})

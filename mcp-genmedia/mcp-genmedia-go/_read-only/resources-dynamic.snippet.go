// Dynamic resource example - user profiles by ID
template := mcp.NewResourceTemplate(
    "users://{id}/profile",
    "User Profile",
    mcp.WithTemplateDescription("Returns user profile information"),
    mcp.WithTemplateMIMEType("application/json"),
)

// Add template with its handler
s.AddResourceTemplate(template, func(ctx context.Context, request mcp.ReadResourceRequest) ([]mcp.ResourceContents, error) {
    // Extract ID from the URI using regex matching
    // The server automatically matches URIs to templates
    userID := extractIDFromURI(request.Params.URI)
    
    profile, err := getUserProfile(userID)  // Your DB/API call here
    if err != nil {
        return nil, err
    }
    
    return []mcp.ResourceContents{
        mcp.TextResourceContents{
            URI:      request.Params.URI,
            MIMEType: "application/json",
            Text:     profile,
        },
    }, nil
})

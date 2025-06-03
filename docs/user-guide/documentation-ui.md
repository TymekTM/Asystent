# Documentation Integration in Web UI

This page explains how to use the documentation system integrated directly in the web UI.

## Accessing Documentation

In version 1.2.0, comprehensive documentation is available directly within the web interface:

1. Log in to the web UI
2. Click on the "Documentation" link in the navigation bar
3. Browse through the available documentation sections

## Documentation Structure

The documentation is organized into several main sections:

### User Guide
- General usage instructions
- Voice interaction guide
- Module documentation
- Daily briefing information
- Web interface guide
- Onboarding process
- Function calling features

### Developer Guide  
- Setup instructions
- Architecture documentation
- Module development guides
- API reference
- Testing guidelines
- Function calling schema development
- Developer playground usage

### API Documentation
- REST API endpoints
- Authentication information
- Request/response formats
- Integration examples

## Navigating Documentation

The documentation viewer provides easy navigation:

1. **Breadcrumb Navigation**: Follow your path through documentation hierarchies
2. **Section Links**: Jump between related documentation sections
3. **Table of Contents**: Quick access to document sections
4. **Search**: Find specific topics within documentation

## Adding Documentation

If you're a developer and want to add or modify documentation:

1. Documentation files are written in Markdown format
2. Files are stored in the `docs/` directory
3. Follow the existing structure and naming conventions
4. New files will automatically appear in the web UI after server restart

## Offline Access

All documentation is available offline through the web UI once the application is running. No internet connection is required to access the documentation after the initial installation.

## Troubleshooting

If you encounter documentation display issues:

1. Check that the application is running with proper permissions
2. Verify the web server has read access to the docs directory
3. Try clearing your browser cache
4. Restart the web server component if necessary

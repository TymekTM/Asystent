# Adding Documentation to the Web UI

This guide explains how to integrate the documentation into the Asystent web interface.

## Overview

To make the documentation accessible directly from the web UI, we'll:

1. Create a new documentation page template
2. Add a route to the Flask application
3. Add a navigation link in the base template
4. Style the documentation display

## Step 1: Create the Documentation Page Template

First, create a new template file for displaying documentation:

1. Create a new file: `web_ui/templates/documentation.html`
2. Implement the template with Markdown rendering capabilities

## Step 2: Add Flask Route Handler

Add routes to `web_ui/app.py` to serve the documentation:

```python
import markdown
import os

# Add at the end of the existing route definitions
@app.route('/documentation')
@login_required
def documentation_main():
    """Main documentation page."""
    with open(os.path.join(app.root_path, '..', 'docs', 'README.md'), 'r', encoding='utf-8') as f:
        content = f.read()
    html_content = markdown.markdown(content, extensions=['fenced_code', 'tables'])
    return render_template('documentation.html', 
                           title="Documentation", 
                           content=html_content,
                           section="main")

@app.route('/documentation/<section>/<path>')
@login_required
def documentation_section(section, path):
    """Display a specific documentation file."""
    try:
        file_path = os.path.join(app.root_path, '..', 'docs', section, f"{path}.md")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        html_content = markdown.markdown(content, extensions=['fenced_code', 'tables'])
        return render_template('documentation.html', 
                               title=f"{path.replace('-', ' ').title()}", 
                               content=html_content,
                               section=section)
    except FileNotFoundError:
        flash("Documentation page not found", "danger")
        return redirect(url_for('documentation_main'))
```

## Step 3: Add Navigation Link

Modify the `base.html` template to include a link to the documentation:

1. Open `web_ui/templates/base.html`
2. Add a new menu item in the navigation bar

```html
<!-- Add this inside the navbar list -->
<li class="nav-item">
    <a class="nav-link {% if request.endpoint == 'documentation_main' or request.endpoint == 'documentation_section' %}active{% endif %}" href="{{ url_for('documentation_main') }}">Documentation</a>
</li>
```

## Step 4: Create the Documentation Template

Create the `documentation.html` template for rendering documentation content:

```html
{% extends "base.html" %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <!-- Sidebar with links -->
        <div class="col-md-3 mb-4">
            <div class="card">
                <div class="card-header">
                    Documentation
                </div>
                <div class="list-group list-group-flush">
                    <a href="{{ url_for('documentation_main') }}" class="list-group-item list-group-item-action {% if section == 'main' %}active{% endif %}">Introduction</a>
                    
                    <div class="list-group-item list-group-item-secondary">User Guide</div>
                    <a href="{{ url_for('documentation_section', section='user-guide', path='README') }}" class="list-group-item list-group-item-action {% if section == 'user-guide' and path == 'README' %}active{% endif %}">Overview</a>
                    <a href="{{ url_for('documentation_section', section='user-guide', path='web-ui') }}" class="list-group-item list-group-item-action {% if section == 'user-guide' and path == 'web-ui' %}active{% endif %}">Web Interface</a>
                    <a href="{{ url_for('documentation_section', section='user-guide', path='voice-interaction') }}" class="list-group-item list-group-item-action {% if section == 'user-guide' and path == 'voice-interaction' %}active{% endif %}">Voice Interaction</a>
                    
                    <div class="list-group-item list-group-item-secondary">Developer Guide</div>
                    <a href="{{ url_for('documentation_section', section='developer', path='README') }}" class="list-group-item list-group-item-action {% if section == 'developer' and path == 'README' %}active{% endif %}">Setup</a>
                    <a href="{{ url_for('documentation_section', section='developer', path='ai-architecture') }}" class="list-group-item list-group-item-action {% if section == 'developer' and path == 'ai-architecture' %}active{% endif %}">AI Architecture</a>
                    <a href="{{ url_for('documentation_section', section='developer', path='plugin-development') }}" class="list-group-item list-group-item-action {% if section == 'developer' and path == 'plugin-development' %}active{% endif %}">Plugin Development</a>
                    
                    <div class="list-group-item list-group-item-secondary">API Reference</div>
                    <a href="{{ url_for('documentation_section', section='api', path='README') }}" class="list-group-item list-group-item-action {% if section == 'api' and path == 'README' %}active{% endif %}">Overview</a>
                    <a href="{{ url_for('documentation_section', section='api', path='rest-endpoints') }}" class="list-group-item list-group-item-action {% if section == 'api' and path == 'rest-endpoints' %}active{% endif %}">REST Endpoints</a>
                </div>
            </div>
        </div>
        
        <!-- Main content -->
        <div class="col-md-9">
            <div class="card">
                <div class="card-body">
                    <div class="markdown-content">
                        {{ content | safe }}
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
    // Add syntax highlighting if needed
    document.addEventListener('DOMContentLoaded', function() {
        // If you add a syntax highlighter like highlight.js
        // hljs.highlightAll();
    });
</script>
{% endblock %}
```

## Step 5: Add Styling for Documentation

Add custom CSS for better documentation rendering:

1. Create or update `web_ui/static/css/style.css`
2. Add documentation-specific styles

```css
/* Documentation Styles */
.markdown-content h1 {
    margin-top: 0.5em;
    margin-bottom: 0.8em;
    font-size: 2rem;
}

.markdown-content h2 {
    margin-top: 1.5em;
    margin-bottom: 0.8em;
    font-size: 1.8rem;
}

.markdown-content h3 {
    margin-top: 1.2em;
    margin-bottom: 0.5em;
    font-size: 1.5rem;
}

.markdown-content pre {
    background-color: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 1em;
    overflow-x: auto;
}

.markdown-content code {
    padding: 0.2em 0.4em;
    background-color: #f5f5f5;
    border-radius: 3px;
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.9em;
}

.markdown-content pre code {
    padding: 0;
    background-color: transparent;
}

.markdown-content table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
}

.markdown-content table th,
.markdown-content table td {
    padding: 0.5em;
    border: 1px solid #e0e0e0;
}

.markdown-content table th {
    background-color: #f5f5f5;
}

.markdown-content img {
    max-width: 100%;
    height: auto;
}

.markdown-content blockquote {
    border-left: 4px solid #e0e0e0;
    padding-left: 1em;
    margin-left: 0;
    color: #666;
}

body[data-bs-theme="dark"] .markdown-content pre,
body[data-bs-theme="dark"] .markdown-content code {
    background-color: #2a2a2a;
    border-color: #3a3a3a;
}

body[data-bs-theme="dark"] .markdown-content table th {
    background-color: #2a2a2a;
}

body[data-bs-theme="dark"] .markdown-content blockquote {
    border-left-color: #3a3a3a;
    color: #aaa;
}
```

## Step 6: Install Required Package

Add the Python Markdown package to handle Markdown rendering:

```bash
pip install markdown
```

And update `requirements.txt`:

```
# Add to existing requirements
markdown>=3.4.0
```

## Step 7: Update Navigation Permissions

Ensure appropriate visibility based on user roles by updating `base.html`:

```html
{% if session.username %}
    {% if session.role == 'user' or session.role == 'dev' %}
        <li class="nav-item">
            <a class="nav-link {% if request.endpoint == 'documentation_main' or request.endpoint == 'documentation_section' %}active{% endif %}" href="{{ url_for('documentation_main') }}">Documentation</a>
        </li>
    {% endif %}
{% endif %}
```

## Additional Enhancements

### Adding Search Functionality

Consider adding search capabilities to the documentation:

1. Create a documentation search endpoint
2. Add a search box to the documentation template
3. Implement client-side or server-side search functionality

### PDF Export

Add the ability to export documentation as PDF:

```python
@app.route('/documentation/export/<section>/<path>')
@login_required
def export_documentation(section, path):
    """Export a documentation page as PDF."""
    # Implementation using a PDF generation library
    # ...
```

# AGENTS.md

## Project: Portable File Transfer (Webview FTP Server)

Build a beautiful, easy-to-use local network file sharing web application with an attractive UI and great UX.

### Technology Stack

- **Backend**: Python 3.11+ with FastAPI + UV for dependency management
- **Frontend**: Single-page HTML/CSS/JS, styled with Tailwind CSS v4 (built via Bun; `src/tailwind/input.css` → `static/css/tailwind.css`). The compiled CSS is committed, so the server runs with no frontend build step.
- **Communication**: REST API + Server-Sent Events for real-time progress
- **File Storage**: Local filesystem with configurable shared directory

### Core Features

1. **File Management**
   - Browse directories and files with folder navigation
   - Upload files with drag-and-drop support
   - Download files and folders (zip compression)
   - Delete files and folders
   - Create new folders
   - Search/filter files
   - File preview for images, videos, PDFs, text files

2. **Sharing**
   - Generate shareable links for individual files
   - Set expiration times for shares
   - Password-protected shares (optional)
   - Track download counts

3. **UI/UX Requirements**
   - Clean, modern interface with smooth animations
   - Dark/light mode toggle
   - Responsive design (mobile + desktop)
   - Progress bars for uploads/downloads
   - Toast notifications for actions
   - Breadcrumb navigation
   - Grid and list view toggle
   - File type icons
   - Drag-and-drop upload zones
   - Keyboard shortcuts

4. **Local Network**
   - Automatically detect local IP address
   - QR code for easy mobile connection
   - Show accessible URL on startup
   - Configurable port

### Project Structure

```
Portable_File_Transfer/
├── AGENTS.md
├── pyproject.toml
├── README.md
├── src/
│   └── swiftshare/
│       ├── __init__.py
│       ├── main.py              # FastAPI app entry point
│       ├── config.py            # Configuration settings
│       ├── models.py            # Pydantic models
│       ├── file_manager.py      # File operations
│       ├── share_manager.py     # Sharing logic
│       └── routers/
│           ├── __init__.py
│           ├── files.py         # File API routes
│           ├── upload.py        # Upload API routes
│           └── shares.py        # Share API routes
├── static/
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
└── tests/
    └── test_api.py
```

### Implementation Steps

1. **Setup**: Initialize project with `pyproject.toml` using UV
   ```bash
   uv init
   uv add fastapi uvicorn python-multipart aiofiles pydantic-settings qrcode
   ```

2. **Backend Core**:
   - Create FastAPI app with CORS middleware
   - Implement file manager with async operations
   - Add file upload with progress tracking
   - Implement zip compression for folder downloads
   - Add share generation with optional passwords
   - Include file type detection and preview support

3. **Frontend**:
   - Build single-page app with vanilla JS or lightweight framework
   - Use CSS Grid/Flexbox for layout
   - Implement drag-and-drop upload zone
   - Add progress indicators using SSE
   - Create modal dialogs for share creation
   - Implement search and filter functionality
   - Add dark/light theme toggle
   - Ensure mobile responsiveness

4. **UI Design Guidelines**:
   - Use modern color scheme (consider gradients, glass morphism)
   - Consistent spacing and typography
   - Smooth transitions and hover effects
   - Clear visual hierarchy
   - Accessible color contrast
   - Loading skeletons for async operations

5. **Testing**:
   - Test file uploads (small and large files)
   - Test download functionality
   - Test share link generation and access
   - Test on mobile devices
   - Verify local network accessibility

### Running the Application

```bash
# Install dependencies
uv sync

# Run development server
uv run uvicorn src.swiftshare.main:app --reload --host 0.0.0.0 --port 8000

# Access from local network at http://<your-ip>:8000
```

### Configuration

Default settings (configurable via environment variables or `.env`):
- `SHARED_DIR`: Directory to share (default: current working directory)
- `PORT`: Server port (default: 8000)
- `HOST`: Bind address (default: 0.0.0.0)
- `MAX_UPLOAD_SIZE`: Maximum file size (default: 2GB)
- `ENABLE_AUTH`: Enable basic auth (default: false)
- `SHARE_EXPIRY_HOURS`: Default share expiration (default: 24 hours)

### Design Principles

- **Simplicity**: One-click access, no complex setup
- **Speed**: Fast file transfers with progress feedback
- **Beauty**: Modern, clean interface that feels premium
- **Accessibility**: Works on any device on the network
- **Reliability**: Robust error handling and recovery

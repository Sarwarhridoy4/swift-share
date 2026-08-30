(function () {
    'use strict';

    const state = {
        currentPath: '',
        viewMode: 'grid',
        theme: localStorage.getItem('theme') || 'light',
        files: [],
        searchQuery: '',
    };

    const API_BASE = window.location.origin;

    function init() {
        applyTheme(state.theme);
        loadConnectionInfo();
        loadFiles();
        setupEventListeners();
        setupKeyboardShortcuts();
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        state.theme = theme;
        localStorage.setItem('theme', theme);
        const icon = document.querySelector('.theme-icon');
        if (icon) icon.textContent = theme === 'dark' ? '☀️' : '🌙';
    }

    function toggleTheme() {
        applyTheme(state.theme === 'dark' ? 'light' : 'dark');
    }

    async function loadConnectionInfo() {
        try {
            const res = await fetch(`${API_BASE}/api/ip`);
            const data = await res.json();
            const url = `http://${data.ip}:${data.port}`;
            document.querySelector('.connection-url').textContent = url;
        } catch (e) {
            document.querySelector('.connection-url').textContent = `${window.location.host}`;
        }
    }

    async function loadFiles() {
        try {
            const res = await fetch(`${API_BASE}/api/files/?path=${encodeURIComponent(state.currentPath)}`);
            if (!res.ok) throw new Error('Failed to load files');
            state.files = await res.json();
            renderFiles();
            updateBreadcrumb();
        } catch (e) {
            showToast(e.message, 'error');
        }
    }

    function renderFiles() {
        const container = document.getElementById('fileList');
        const emptyState = document.getElementById('emptyState');
        let filtered = state.files;

        if (state.searchQuery) {
            const q = state.searchQuery.toLowerCase();
            filtered = filtered.filter(f => f.name.toLowerCase().includes(q));
        }

        filtered.sort((a, b) => {
            if (a.is_dir !== b.is_dir) return b.is_dir ? 1 : -1;
            return a.name.localeCompare(b.name);
        });

        if (filtered.length === 0) {
            container.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }

        emptyState.style.display = 'none';
        container.innerHTML = filtered.map(file => {
            const icon = getFileIcon(file.name, file.is_dir);
            const isDir = file.is_dir;
            const downloadAction = isDir
                ? `<button class="file-action" data-act="download-folder" title="Download folder as zip">⬇️</button>`
                : `<button class="file-action" data-act="download" title="Download">⬇️</button>`;
            return `
                <div class="file-item" data-path="${file.path}" data-name="${file.name}" data-is-dir="${file.is_dir}">
                    <div class="file-actions">
                        ${downloadAction}
                        <button class="file-action" data-act="copy-link" title="Copy direct link">🔗</button>
                        <button class="file-action" data-act="share" title="Create share">🔐</button>
                    </div>
                    <div class="file-icon">${icon}</div>
                    <div class="file-info">
                        <div class="file-name" title="${file.name}">${file.name}</div>
                        <div class="file-size">${formatSize(file.size)}</div>
                    </div>
                </div>
            `;
        }).join('');

        container.querySelectorAll('.file-item').forEach(item => {
            item.addEventListener('click', (e) => handleFileClick(item, e));
            item.addEventListener('contextmenu', (e) => showContextMenu(e, item));
            item.querySelectorAll('.file-action').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const act = btn.dataset.act;
                    const path = item.dataset.path;
                    const isDir = item.dataset.isDir === 'true';
                    if (act === 'download') downloadFile(path);
                    else if (act === 'download-folder') downloadFolder(path);
                    else if (act === 'share') openShareModal(path);
                    else if (act === 'copy-link') copyDirectLink(path, isDir);
                });
            });
        });
    }

    function copyDirectLink(path, isDir) {
        const endpoint = isDir ? 'download-folder' : 'download';
        const link = `${API_BASE}/api/files/${endpoint}?path=${encodeURIComponent(path)}`;
        navigator.clipboard.writeText(link).then(() => {
            showToast('Direct link copied to clipboard', 'success');
        }).catch(() => {
            showToast('Copy failed', 'error');
        });
    }

    function getFileIcon(name, isDir) {
        if (isDir) return '📁';
        const ext = name.split('.').pop().toLowerCase();
        const icons = {
            'pdf': '📄', 'doc': '📝', 'docx': '📝', 'txt': '📃',
            'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'svg': '🖼️', 'webp': '🖼️',
            'mp4': '🎬', 'mov': '🎬', 'avi': '🎬', 'mkv': '🎬',
            'mp3': '🎵', 'wav': '🎵', 'flac': '🎵',
            'zip': '📦', 'rar': '📦', '7z': '📦', 'tar': '📦', 'gz': '📦',
            'js': '📜', 'ts': '📜', 'py': '📜', 'html': '📜', 'css': '📜',
            'xls': '📊', 'xlsx': '📊', 'csv': '📊',
            'ppt': '📽️', 'pptx': '📽️',
        };
        return icons[ext] || '📎';
    }

    function formatSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function handleFileClick(item, e) {
        if (e.ctrlKey || e.metaKey) return;
        const path = item.dataset.path;
        const isDir = item.dataset.isDir === 'true';
        if (isDir) {
            navigateTo(path);
        } else {
            previewFile(path);
        }
    }

    function navigateTo(path) {
        state.currentPath = path;
        state.searchQuery = '';
        document.getElementById('searchInput').value = '';
        loadFiles();
    }

    function updateBreadcrumb() {
        const breadcrumb = document.getElementById('breadcrumb');
        const parts = state.currentPath ? state.currentPath.split('/').filter(Boolean) : [];
        let html = `<button class="breadcrumb-item" data-path="">🏠 Home</button>`;
        let current = '';
        parts.forEach((part, i) => {
            current += (current ? '/' : '') + part;
            html += `<span class="breadcrumb-separator">/</span><button class="breadcrumb-item" data-path="${current}">${part}</button>`;
        });
        breadcrumb.innerHTML = html;
        breadcrumb.querySelectorAll('.breadcrumb-item').forEach(btn => {
            btn.addEventListener('click', () => navigateTo(btn.dataset.path));
        });
    }

    async function createNewFolder() {
        const name = prompt('Enter folder name:');
        if (!name) return;
        try {
            const res = await fetch(`${API_BASE}/api/files/mkdir`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: state.currentPath, name }),
            });
            if (!res.ok) throw new Error('Failed to create folder');
            showToast('Folder created', 'success');
            loadFiles();
        } catch (e) {
            showToast(e.message, 'error');
        }
    }

    async function deleteItem(path) {
        if (!confirm('Are you sure you want to delete this item?')) return;
        try {
            const res = await fetch(`${API_BASE}/api/files/?path=${encodeURIComponent(path)}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Failed to delete');
            showToast('Deleted successfully', 'success');
            loadFiles();
        } catch (e) {
            showToast(e.message, 'error');
        }
    }

    async function downloadFile(path) {
        try {
            const res = await fetch(`${API_BASE}/api/files/download?path=${encodeURIComponent(path)}`);
            if (!res.ok) throw new Error('Download failed');
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = res.headers.get('Content-Disposition')?.split('filename=')[1]?.replace(/"/g, '') || 'download';
            a.click();
            window.URL.revokeObjectURL(url);
            showToast('Download started', 'success');
        } catch (e) {
            showToast(e.message, 'error');
        }
    }

    async function downloadFolder(path) {
        try {
            const res = await fetch(`${API_BASE}/api/files/download-folder?path=${encodeURIComponent(path)}`);
            if (!res.ok) throw new Error('Download failed');
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = res.headers.get('Content-Disposition')?.split('filename=')[1]?.replace(/"/g, '') || 'download.zip';
            a.click();
            window.URL.revokeObjectURL(url);
            showToast('Download started', 'success');
        } catch (e) {
            showToast(e.message, 'error');
        }
    }

    async function previewFile(path) {
        try {
            const mimeRes = await fetch(`${API_BASE}/api/files/mime-type?path=${encodeURIComponent(path)}`);
            const mimeData = await mimeRes.json();
            const mime = mimeData.mime_type || '';

            const modal = document.getElementById('previewModal');
            const title = document.getElementById('previewTitle');
            const content = document.getElementById('previewContent');
            title.textContent = path.split('/').pop();
            content.innerHTML = '<div style="text-align:center;padding:40px;">Loading...</div>';
            modal.style.display = 'flex';

            if (mime.startsWith('image/')) {
                const res = await fetch(`${API_BASE}/api/files/download?path=${encodeURIComponent(path)}`);
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                content.innerHTML = `<img src="${url}" style="max-width:100%;max-height:70vh;border-radius:8px;">`;
            } else if (mime.startsWith('video/')) {
                const res = await fetch(`${API_BASE}/api/files/download?path=${encodeURIComponent(path)}`);
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                content.innerHTML = `<video src="${url}" controls style="max-width:100%;max-height:70vh;border-radius:8px;"></video>`;
            } else if (mime.startsWith('audio/')) {
                const res = await fetch(`${API_BASE}/api/files/download?path=${encodeURIComponent(path)}`);
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                content.innerHTML = `<audio src="${url}" controls style="width:100%;"></audio>`;
            } else if (mime === 'application/pdf') {
                const res = await fetch(`${API_BASE}/api/files/download?path=${encodeURIComponent(path)}`);
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                content.innerHTML = `<iframe src="${url}" style="width:100%;height:70vh;border:none;border-radius:8px;"></iframe>`;
            } else {
                const fileName = path.split('/').pop();
                content.innerHTML = `
                    <div style="text-align:center;padding:48px 24px;">
                        <div style="font-size:56px;margin-bottom:16px;">📄</div>
                        <p style="color:var(--text-secondary);margin-bottom:20px;">
                            Preview is not available for this file type.<br>Download it to view the contents.
                        </p>
                        <button class="btn btn-primary" id="previewDownloadBtn">⬇ Download to view</button>
                    </div>`;
                document.getElementById('previewDownloadBtn').addEventListener('click', () => downloadFile(path));
            }
        } catch (e) {
            showToast(e.message, 'error');
            document.getElementById('previewModal').style.display = 'none';
        }
    }

    function openShareModal(path) {
        document.getElementById('sharePath').value = path;
        document.getElementById('shareResult').style.display = 'none';
        document.getElementById('shareForm').style.display = 'block';
        document.getElementById('shareModal').style.display = 'flex';
    }

    async function createShare(e) {
        e.preventDefault();
        const path = document.getElementById('sharePath').value;
        const expiresIn = parseInt(document.getElementById('shareExpiry').value);
        const password = document.getElementById('sharePassword').value || undefined;

        try {
            const res = await fetch(`${API_BASE}/api/shares/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path, expires_in_hours: expiresIn, password }),
            });
            if (!res.ok) throw new Error('Failed to create share');
            const share = await res.json();
            const link = `${API_BASE}/api/shares/${share.id}?password=${password || ''}`;
            document.getElementById('shareLink').value = link;
            document.getElementById('shareResult').style.display = 'block';
            document.getElementById('shareForm').style.display = 'none';
            showToast('Share created', 'success');
        } catch (e) {
            showToast(e.message, 'error');
        }
    }

    function copyShareLink() {
        const input = document.getElementById('shareLink');
        input.select();
        document.execCommand('copy');
        showToast('Copied to clipboard', 'success');
    }

    function showContextMenu(e, item) {
        e.preventDefault();
        const path = item.dataset.path;
        const isDir = item.dataset.isDir === 'true';
        const menu = document.getElementById('contextMenu');
        menu.innerHTML = `
            ${isDir ? '' : `<button class="context-menu-item" data-action="preview">👁️ Preview</button>`}
            <button class="context-menu-item" data-action="download">⬇️ Download</button>
            <button class="context-menu-item" data-action="share">🔗 Share</button>
            <div class="context-menu-divider"></div>
            <button class="context-menu-item danger" data-action="delete">🗑️ Delete</button>
        `;
        menu.style.display = 'block';
        menu.style.left = `${e.clientX}px`;
        menu.style.top = `${e.clientY}px`;

        menu.querySelectorAll('.context-menu-item').forEach(btn => {
            btn.addEventListener('click', () => {
                menu.style.display = 'none';
                const action = btn.dataset.action;
                if (action === 'preview') previewFile(path);
                else if (action === 'download') isDir ? downloadFolder(path) : downloadFile(path);
                else if (action === 'share') openShareModal(path);
                else if (action === 'delete') deleteItem(path);
            });
        });
    }

    function showToast(message, type = 'success') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async function uploadFiles(files) {
        const formData = new FormData();
        formData.append('path', state.currentPath);
        for (const file of files) {
            formData.append('file', file);
        }

        showToast('Uploading files...', 'success');
        try {
            const res = await fetch(`${API_BASE}/api/upload/`, {
                method: 'POST',
                body: formData,
            });
            if (!res.ok) throw new Error('Upload failed');
            showToast('Upload complete', 'success');
            loadFiles();
        } catch (e) {
            showToast(e.message, 'error');
        }
    }

    function setupEventListeners() {
        document.getElementById('themeToggle').addEventListener('click', toggleTheme);
        document.getElementById('newFolderBtn').addEventListener('click', createNewFolder);
        document.getElementById('fileInput').addEventListener('change', (e) => {
            if (e.target.files.length) uploadFiles(e.target.files);
        });
        document.getElementById('shareForm').addEventListener('submit', createShare);
        document.getElementById('copyShareLink').addEventListener('click', copyShareLink);

        document.getElementById('gridViewBtn').addEventListener('click', () => setViewMode('grid'));
        document.getElementById('listViewBtn').addEventListener('click', () => setViewMode('list'));

        document.getElementById('searchInput').addEventListener('input', (e) => {
            state.searchQuery = e.target.value;
            renderFiles();
        });

        document.querySelectorAll('[data-close]').forEach(el => {
            el.addEventListener('click', () => {
                document.getElementById(el.dataset.close).style.display = 'none';
            });
        });

        const dropZone = document.getElementById('dropZone');
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });
        dropZone.addEventListener('dragenter', () => dropZone.classList.add('drag-over'));
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
        dropZone.addEventListener('drop', (e) => {
            dropZone.classList.remove('drag-over');
            if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.context-menu')) {
                document.getElementById('contextMenu').style.display = 'none';
            }
        });
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function setViewMode(mode) {
        state.viewMode = mode;
        const container = document.getElementById('fileContainer');
        container.classList.remove('grid-view', 'list-view');
        container.classList.add(`${mode}-view`);
        document.getElementById('gridViewBtn').classList.toggle('active', mode === 'grid');
        document.getElementById('listViewBtn').classList.toggle('active', mode === 'list');
    }

    function setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal').forEach(m => m.style.display = 'none');
                document.getElementById('contextMenu').style.display = 'none';
            }
            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                e.preventDefault();
                document.getElementById('searchInput').focus();
            }
        });
    }

    document.addEventListener('DOMContentLoaded', init);
})();

import React, { useState, useEffect, useCallback, useRef } from 'react';
import io, { Socket } from 'socket.io-client';
import { API_BASE, formatSize, getFileIcon } from '@/lib/utils';
import type { FileItem, Theme } from '@/types';
import { Sun, Moon, Upload, Share2, FileText, Image, Video, Music, Folder, Grid, List, Search, X, Copy, Download, QrCode, Smartphone } from 'lucide-react';
import Header from '@/components/Header';
import Toolbar from '@/components/Toolbar';
import StatsBar from '@/components/StatsBar';
import Breadcrumb from '@/components/Breadcrumb';
import FileBrowser from '@/components/FileBrowser';
import TransferPanel from '@/components/TransferPanel';
import ToastContainer from '@/components/ToastContainer';
import QRModal from '@/components/QRModal';
import NewFolderModal from '@/components/NewFolderModal';
import ShareModal from '@/components/ShareModal';
import PreviewModal from '@/components/PreviewModal';
import ConfirmModal from '@/components/ConfirmModal';
import ContextMenu from '@/components/ContextMenu';

export default function App() {
  const [theme, setTheme] = useState<Theme>((() => {
    const saved = localStorage.getItem('theme') as Theme | null;
    return saved || 'light';
  })());
  const [currentPath, setCurrentPath] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [files, setFiles] = useState<FileItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [sort, setSort] = useState<'name' | 'name-desc' | 'size' | 'size-desc'>('name');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [etag, setEtag] = useState<string | null>(null);
  const [stats, setStats] = useState({ files: 0, folders: 0, size: 0, shares: 0 });
  const [connectionInfo, setConnectionInfo] = useState<{ ip: string; port: number } | null>(null);
  const [modals, setModals] = useState<{ qr: boolean; newFolder: boolean; share: boolean; preview: boolean; confirm: boolean }>({ qr: false, newFolder: false, share: false, preview: false, confirm: false });
  const [sharePath, setSharePath] = useState('');
  const [previewPath, setPreviewPath] = useState('');
  const [confirmAction, setConfirmAction] = useState<{ title: string; message: string; onConfirm: () => void } | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; path: string; isDir: boolean } | null>(null);
  const [transfer, setTransfer] = useState<{ name: string; loaded: number; total: number; percent: number } | null>(null);
  const [toasts, setToasts] = useState<Array<{ id: string; message: string; type: 'success' | 'error' }>>([]);
  const [qrUrl, setQrUrl] = useState('');
  const [shareLink, setShareLink] = useState('');

  const socketRef = useRef<Socket | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const toastTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const cancelRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  useEffect(() => {
    cancelRequest();
    abortControllerRef.current = new AbortController();
    setLoading(true);

    fetch(`${API_BASE}/api/files/?path=${encodeURIComponent(currentPath)}`, {
      signal: abortControllerRef.current.signal,
    })
      .then(async (res) => {
        if (res.status === 304) {
          setLoading(false);
          return;
        }
        if (!res.ok) throw new Error('Failed to load files');
        const data = await res.json();
        setEtag(res.headers.get('etag') || null);
        setFiles(data.items || []);
        setStats({
          files: data.items?.filter((f: FileItem) => !f.is_dir).length || 0,
          folders: data.items?.filter((f: FileItem) => f.is_dir).length || 0,
          size: data.items?.reduce((sum: number, f: FileItem) => sum + (f.size || 0), 0) || 0,
          shares: stats.shares,
        });
        setSelectedIds(new Set());
      })
      .catch((e) => {
        if (e.name === 'AbortError') return;
        addToast(e.message, 'error');
        setLoading(false);
      })
      .finally(() => setLoading(false));
  }, [currentPath, cancelRequest, stats.shares]);

  useEffect(() => {
    fetch(`${API_BASE}/api/ip`)
      .then((res) => res.json())
      .then((data) => {
        setConnectionInfo(data);
        setQrUrl(`http://${data.ip}:${data.port}`);
      })
      .catch(() => {
        setQrUrl(`http://${window.location.host}`);
      });
  }, []);

  useEffect(() => {
    const socket = io();
    socketRef.current = socket;

    socket.on('connect', () => {
      socket.emit('join_room', { room: 'transfers' });
      socket.emit('join_room', { room: 'files' });
    });

    socket.on('transfer:started', (data: any) => {
      setTransfer({ name: data.filename, loaded: 0, total: data.total, percent: 0 });
    });

    socket.on('transfer:progress', (data: any) => {
      if (transfer) {
        setTransfer({ ...transfer, loaded: data.loaded, total: data.total, percent: Math.round((data.loaded / Math.max(data.total, 1)) * 100) });
      }
    });

    socket.on('transfer:completed', () => {
      addToast('Transfer completed', 'success');
      setTimeout(() => { setTransfer(null); loadFiles(); }, 1000);
    });

    socket.on('transfer:error', (data: any) => {
      addToast(data.error || 'Transfer failed', 'error');
      setTransfer(null);
    });

    socket.on('upload:complete', (data: any) => {
      addToast(`Upload complete: ${data.filename}`, 'success');
      loadFiles();
    });

    socket.on('file:changed', (data: any) => {
      if (data.path === currentPath || data.path.startsWith(currentPath + '/')) {
        loadFiles();
      }
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [currentPath]);

  const loadFiles = useCallback(() => {
    cancelRequest();
    abortControllerRef.current = new AbortController();
    setLoading(true);

    fetch(`${API_BASE}/api/files/?path=${encodeURIComponent(currentPath)}`, {
      signal: abortControllerRef.current.signal,
    })
      .then(async (res) => {
        if (res.status === 304) { setLoading(false); return; }
        if (!res.ok) throw new Error('Failed to load files');
        const data = await res.json();
        setEtag(res.headers.get('etag') || null);
        setFiles(data.items || []);
        setStats((prev) => ({
          files: data.items?.filter((f: FileItem) => !f.is_dir).length || 0,
          folders: data.items?.filter((f: FileItem) => f.is_dir).length || 0,
          size: data.items?.reduce((sum: number, f: FileItem) => sum + (f.size || 0), 0) || 0,
          shares: prev.shares,
        }));
        setSelectedIds(new Set());
      })
      .catch((e) => {
        if (e.name === 'AbortError') return;
        addToast(e.message, 'error');
        setLoading(false);
      })
      .finally(() => setLoading(false));
  }, [currentPath, cancelRequest]);

  const addToast = (message: string, type: 'success' | 'error') => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { id, message, type }]);
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
    toastTimeoutRef.current = setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  };

  const toggleSelect = (path: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const navigateTo = (path: string) => {
    setCurrentPath(path);
    setSearchQuery('');
    setSelectedIds(new Set());
  };

  const handleFileClick = (file: FileItem) => {
    if (file.is_dir) {
      navigateTo(file.path);
    } else {
      setPreviewPath(file.path);
      setModals((prev) => ({ ...prev, preview: true }));
    }
  };

  const copyDirectLink = (path: string, isDir: boolean) => {
    const endpoint = isDir ? 'download-folder' : 'download';
    const link = `${API_BASE}/api/files/${endpoint}?path=${encodeURIComponent(path)}`;
    navigator.clipboard.writeText(link).then(() => {
      addToast('Direct link copied', 'success');
    }).catch(() => addToast('Copy failed', 'error'));
  };

  const downloadFile = (path: string) => {
    const name = path.split('/').pop() || 'download';
    window.location.href = `${API_BASE}/api/files/download?path=${encodeURIComponent(path)}`;
  };

  const downloadFolder = (path: string) => {
    const name = (path.split('/').pop() || 'folder') + '.zip';
    window.location.href = `${API_BASE}/api/files/download-folder?path=${encodeURIComponent(path)}`;
  };

  const deleteItem = async (path: string) => {
    if (!window.confirm('Are you sure you want to delete this item?')) return;
    try {
      const res = await fetch(`${API_BASE}/api/files/?path=${encodeURIComponent(path)}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete');
      addToast('Deleted', 'success');
      loadFiles();
    } catch (e: any) {
      addToast(e.message, 'error');
    }
  };

  const uploadFiles = (files: FileList) => {
    for (const file of files) {
      uploadFile(file);
    }
  };

  const uploadFile = (file: File) => {
    const formData = new FormData();
    formData.append('path', currentPath);
    formData.append('file', file);

    setTransfer({ name: file.name, loaded: 0, total: file.size, percent: 0 });

    const xhr = new XMLHttpRequest();
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        setTransfer({ name: file.name, loaded: e.loaded, total: e.total, percent: Math.round((e.loaded / e.total) * 100) });
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        addToast('Upload complete', 'success');
        loadFiles();
      } else {
        addToast('Upload failed', 'error');
      }
      setTransfer(null);
    };

    xhr.onerror = () => {
      addToast('Upload failed', 'error');
      setTransfer(null);
    };

    xhr.open('POST', `${API_BASE}/api/upload/`);
    xhr.send(formData);
  };

  const createFolder = async (name: string) => {
    if (!name.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/api/files/mkdir`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: currentPath, name: name.trim() }),
      });
      if (!res.ok) throw new Error('Failed to create folder');
      addToast('Folder created', 'success');
      setModals((prev) => ({ ...prev, newFolder: false }));
      loadFiles();
    } catch (e: any) {
      addToast(e.message, 'error');
    }
  };

  const createShare = async (expiresIn: number, password?: string) => {
    if (!sharePath) return;
    try {
      const res = await fetch(`${API_BASE}/api/shares/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: sharePath, expires_in_hours: expiresIn, password }),
      });
      if (!res.ok) throw new Error('Failed to create share');
      const data = await res.json();
      const link = `${API_BASE}/api/shares/${data.id}?password=${password || ''}`;
      setShareLink(link);
      setModals((prev) => ({ ...prev, share: false, preview: false }));
      addToast('Share created', 'success');
    } catch (e: any) {
      addToast(e.message, 'error');
    }
  };

  const copyShareLink = () => {
    navigator.clipboard.writeText(shareLink).then(() => addToast('Copied to clipboard', 'success'));
  };

  const filteredFiles = files.filter((f) => f.name.toLowerCase().includes(searchQuery.toLowerCase())).sort((a, b) => {
    if (a.is_dir !== b.is_dir) return b.is_dir ? 1 : -1;
    if (sort === 'name') return a.name.localeCompare(b.name);
    if (sort === 'name-desc') return b.name.localeCompare(a.name);
    if (sort === 'size') return (b.size || 0) - (a.size || 0);
    return (a.size || 0) - (b.size || 0);
  });

  const openContextMenu = (e: React.MouseEvent, path: string, isDir: boolean) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, path, isDir });
  };

  return (
    <div className="app-shell" onContextMenu={(e) => {
      if (!contextMenu) return;
      const rect = (e.target as HTMLElement).closest('.context-menu');
      if (!rect) setContextMenu(null);
    }}>
      <Header
        theme={theme}
        toggleTheme={() => setTheme((prev) => (prev === 'light' ? 'dark' : 'light'))}
        connectionInfo={connectionInfo}
        qrUrl={qrUrl}
        onOpenQR={() => setModals((prev) => ({ ...prev, qr: true }))}
      />
      <main className="app-main">
        <StatsBar files={stats.files} folders={stats.folders} size={stats.size} shares={stats.shares} />
        <Breadcrumb currentPath={currentPath} onNavigate={navigateTo} />
        <Toolbar
          viewMode={viewMode}
          setViewMode={setViewMode}
          sort={sort}
          setSort={setSort}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          onUploadClick={() => document.getElementById('file-input')?.click()}
          onNewFolderClick={() => setModals((prev) => ({ ...prev, newFolder: true }))}
          onDropFiles={uploadFiles}
        />
        <input type="file" id="file-input" multiple hidden accept="*" onChange={(e) => e.target.files && uploadFiles(e.target.files)} />

        {loading && (
          <div className="skeleton-grid">
            {[1,2,3,4,5,6].map((i) => (
              <div key={i} className="skeleton-item">
                <div className="skeleton-avatar"></div>
                <div className="skeleton-line"></div>
                <div className="skeleton-line short"></div>
              </div>
            ))}
          </div>
        )}

        {!loading && filteredFiles.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">📭</div>
            <h2 className="empty-title">This folder is empty</h2>
            <p className="empty-subtitle">No files here yet. Upload some files or create a new folder to get started.</p>
            <div className="empty-actions">
              <button className="btn-primary" onClick={() => document.getElementById('file-input')?.click()}>Upload files</button>
              <button className="btn-ghost" onClick={() => setModals((prev) => ({ ...prev, newFolder: true }))}>New folder</button>
            </div>
          </div>
        )}

        {!loading && filteredFiles.length > 0 && (
          <FileBrowser
            files={filteredFiles}
            viewMode={viewMode}
            selectedIds={selectedIds}
            onFileClick={handleFileClick}
            onToggleSelect={toggleSelect}
            onDownload={downloadFile}
            onDownloadFolder={downloadFolder}
            onCopyLink={copyDirectLink}
            onShare={(path) => { setSharePath(path); setModals((prev) => ({ ...prev, share: true })); }}
            onDelete={deleteItem}
            onContextMenu={openContextMenu}
          />
        )}
      </main>

      <TransferPanel
        transfer={transfer}
        onCancel={() => setTransfer(null)}
      />
      <ToastContainer toasts={toasts} />

      <QRModal open={modals.qr} onClose={() => setModals((prev) => ({ ...prev, qr: false }))} qrUrl={qrUrl} />
      <NewFolderModal open={modals.newFolder} onClose={() => setModals((prev) => ({ ...prev, newFolder: false }))} onCreate={createFolder} />
      <ShareModal open={modals.share} onClose={() => setModals((prev) => ({ ...prev, share: false }))} path={sharePath} expiresIn={24} onCreate={createShare} onCopyLink={copyShareLink} link={shareLink} />
      <PreviewModal open={modals.preview} onClose={() => setModals((prev) => ({ ...prev, preview: false }))} path={previewPath} />
      <ConfirmModal open={!!confirmAction} onClose={() => setConfirmAction(null)} title={confirmAction?.title || ''} message={confirmAction?.message || ''} onConfirm={() => { confirmAction?.onConfirm(); setConfirmAction(null); }} onCancel={() => setConfirmAction(null)} />
      <ContextMenu open={!!contextMenu} x={contextMenu?.x || 0} y={contextMenu?.y || 0} path={contextMenu?.path || ''} isDir={contextMenu?.isDir || false} onPreview={() => { setPreviewPath(contextMenu?.path || ''); setModals((prev) => ({ ...prev, preview: true })); setContextMenu(null); }} onDownload={() => { const cm = contextMenu; if (cm) cm.isDir ? downloadFolder(cm.path) : downloadFile(cm.path); setContextMenu(null); }} onShare={() => { setSharePath(contextMenu?.path || ''); setModals((prev) => ({ ...prev, share: true })); setContextMenu(null); }} onDelete={() => { deleteItem(contextMenu?.path || ''); setContextMenu(null); }} />
    </div>
  );
}

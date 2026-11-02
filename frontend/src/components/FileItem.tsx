import React from 'react';
import { Download, Link as LinkIcon, Share2, Eye } from 'lucide-react';

interface FileItemProps {
  file: {
    name: string;
    path: string;
    is_dir: boolean;
    size: number;
    modified: string;
  };
  viewMode: 'grid' | 'list';
  selected: boolean;
  onClick: (file: any) => void;
  onToggleSelect: (path: string) => void;
  onDownload: (path: string) => void;
  onDownloadFolder: (path: string) => void;
  onCopyLink: (path: string, isDir: boolean) => void;
  onShare: (path: string) => void;
  onDelete: (path: string) => void;
  onContextMenu: (e: React.MouseEvent, path: string, isDir: boolean) => void;
}

export default function FileItemComponent({
  file, viewMode, selected, onClick, onToggleSelect, onDownload, onDownloadFolder, onCopyLink, onShare, onDelete, onContextMenu,
}: FileItemProps) {
  const ext = file.name.split('.').pop()?.toLowerCase() || '';
  const icons: Record<string, string> = {
    pdf: '📄', doc: '📝', docx: '📝', txt: '📃',
    jpg: '🖼️', jpeg: '🖼️', png: '🖼️', gif: '🖼️', svg: '🖼️', webp: '🖼️',
    mp4: '🎬', mov: '🎬', avi: '🎬', mkv: '🎬',
    mp3: '🎵', wav: '🎵', flac: '🎵',
    zip: '📦', rar: '📦', '7z': '📦', tar: '📦', gz: '📦',
    js: '📜', ts: '📜', py: '📜', html: '📜', css: '📜',
    xls: '📊', xlsx: '📊', csv: '📊',
    ppt: '📽️', pptx: '📽️',
  };
  const icon = file.is_dir ? '📁' : (icons[ext] || '📎');

  const handleClick = (e: React.MouseEvent) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      onToggleSelect(file.path);
    } else {
      onClick(file);
    }
  };

  return (
    <div
      className={`file-item ${selected ? 'selected' : ''}`}
      onClick={handleClick}
      onContextMenu={(e) => onContextMenu(e, file.path, file.is_dir)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick(file);
        }
      }}
      role="button"
      tabIndex={0}
    >
      <div className="file-actions">
        {file.is_dir ? (
          <button className="file-action" onClick={(e) => { e.stopPropagation(); onDownloadFolder(file.path); }} title="Download folder as ZIP">
            <Download size={16} />
          </button>
        ) : (
          <button className="file-action" onClick={(e) => { e.stopPropagation(); onDownload(file.path); }} title="Download">
            <Download size={16} />
          </button>
        )}
        <button className="file-action" onClick={(e) => { e.stopPropagation(); onCopyLink(file.path, file.is_dir); }} title="Copy direct link">
          <LinkIcon size={16} />
        </button>
        <button className="file-action" onClick={(e) => { e.stopPropagation(); onShare(file.path); }} title="Create share">
          <Share2 size={16} />
        </button>
      </div>
      <div className="file-icon">{icon}</div>
      <div className="file-info">
        <div className="file-name" title={file.name}>{file.name}</div>
        <div className="file-meta">
          <div className="file-size">{file.size === 0 ? '0 B' : (file.size / 1024 / 1024).toFixed(2) + ' MB'}</div>
          <div className="file-date">{new Date(file.modified).toLocaleDateString()}</div>
        </div>
      </div>
    </div>
  );
}

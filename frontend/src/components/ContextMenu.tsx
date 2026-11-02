import React from 'react';
import { Download, Share2, Trash2, X, Eye } from 'lucide-react';

interface ContextMenuProps {
  open: boolean;
  x: number;
  y: number;
  path: string;
  isDir: boolean;
  onPreview: () => void;
  onDownload: () => void;
  onShare: () => void;
  onDelete: () => void;
}

export default function ContextMenu({ open, x, y, path, isDir, onPreview, onDownload, onShare, onDelete }: ContextMenuProps) {
  if (!open) return null;

  return (
    <div className="context-menu" style={{ left: x, top: y }}>
      {!isDir && (
        <button className="context-menu-item" onClick={onPreview}>
          <Eye size={16} className="mr-2" /> Preview
        </button>
      )}
      <button className="context-menu-item" onClick={onDownload}>
        <Download size={16} className="mr-2" /> Download
      </button>
      <button className="context-menu-item" onClick={onShare}>
        <Share2 size={16} className="mr-2" /> Share
      </button>
      <div className="context-menu-divider" />
      <button className="context-menu-item danger" onClick={onDelete}>
        <Trash2 size={16} className="mr-2" /> Delete
      </button>
    </div>
  );
}

import React from 'react';
import { formatSize, getFileIcon } from '@/lib/utils';
import type { FileItem as FileItemType } from '@/types';
import FileItemComponent from './FileItem';

interface FileBrowserProps {
  files: FileItemType[];
  viewMode: 'grid' | 'list';
  selectedIds: Set<string>;
  onFileClick: (file: FileItemType) => void;
  onToggleSelect: (path: string) => void;
  onDownload: (path: string) => void;
  onDownloadFolder: (path: string) => void;
  onCopyLink: (path: string, isDir: boolean) => void;
  onShare: (path: string) => void;
  onDelete: (path: string) => void;
  onContextMenu: (e: React.MouseEvent, path: string, isDir: boolean) => void;
}

export default function FileBrowser({
  files, viewMode, selectedIds, onFileClick, onToggleSelect, onDownload, onDownloadFolder, onCopyLink, onShare, onDelete, onContextMenu,
}: FileBrowserProps) {
  return (
    <div className={`file-list ${viewMode}-view`}>
      {files.map((file) => (
        <FileItemComponent
          key={file.path}
          file={file}
          viewMode={viewMode}
          selected={selectedIds.has(file.path)}
          onClick={onFileClick}
          onToggleSelect={onToggleSelect}
          onDownload={onDownload}
          onDownloadFolder={onDownloadFolder}
          onCopyLink={onCopyLink}
          onShare={onShare}
          onDelete={onDelete}
          onContextMenu={onContextMenu}
        />
      ))}
    </div>
  );
}

import React from 'react';
import { Search, Grid, List, Upload, Plus } from 'lucide-react';

interface ToolbarProps {
  viewMode: 'grid' | 'list';
  setViewMode: (mode: 'grid' | 'list') => void;
  sort: string;
  setSort: (sort: string) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  onUploadClick: () => void;
  onNewFolderClick: () => void;
  onDropFiles: (files: FileList) => void;
}

export default function Toolbar({ viewMode, setViewMode, sort, setSort, searchQuery, setSearchQuery, onUploadClick, onNewFolderClick, onDropFiles }: ToolbarProps) {
  return (
    <div className="toolbar" onDragOver={(e) => e.preventDefault()} onDrop={(e) => {
      e.preventDefault();
      if (e.dataTransfer.files.length) onDropFiles(e.dataTransfer.files);
    }}>
      <div className="toolbar-left">
        <div className="search-wrapper relative">
          <Search className="search-icon absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" size={16} />
          <input
            type="text"
            id="search-input"
            placeholder="Search files…"
            autoComplete="off"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input w-full rounded-full border border-white/60 bg-white/70 pl-10 pr-4 py-2.5 text-sm text-slate-700 outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-300/50 backdrop-blur transition dark:border-white/10 dark:bg-slate-800/70 dark:text-slate-100"
            aria-label="Search files"
          />
        </div>
        <div className="view-toggle" role="group" aria-label="View mode">
          <button
            className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`}
            onClick={() => setViewMode('grid')}
            aria-pressed={viewMode === 'grid'}
            title="Grid view"
          >
            <Grid size={18} />
          </button>
          <button
            className={`view-btn ${viewMode === 'list' ? 'active' : ''}`}
            onClick={() => setViewMode('list')}
            aria-pressed={viewMode === 'list'}
            title="List view"
          >
            <List size={18} />
          </button>
        </div>
      </div>
      <div className="toolbar-right">
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="form-input appearance-none bg-white/80 dark:bg-slate-800 pr-10"
          aria-label="Sort by"
        >
          <option value="name">Name (A-Z)</option>
          <option value="name-desc">Name (Z-A)</option>
          <option value="size">Size (Largest)</option>
          <option value="size-desc">Size (Smallest)</option>
        </select>
        <button className="btn-ghost" onClick={onNewFolderClick} title="New folder" aria-label="New folder">
          <Plus className="text-lg" /> New Folder
        </button>
        <button className="btn-primary" onClick={onUploadClick} title="Upload files" aria-label="Upload files">
          <Upload className="text-lg" /> Upload
        </button>
      </div>
    </div>
  );
}

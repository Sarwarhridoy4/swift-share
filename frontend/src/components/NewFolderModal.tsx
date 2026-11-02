import React, { useState } from 'react';
import { Plus, X } from 'lucide-react';

interface NewFolderModalProps {
  open: boolean;
  onClose: () => void;
  onCreate: (name: string) => void;
}

export default function NewFolderModal({ open, onClose, onCreate }: NewFolderModalProps) {
  const [name, setName] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCreate(name);
  };

  if (!open) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-backdrop" onClick={onClose} />
      <div className="modal">
        <div className="modal-header">
          <h2 className="modal-title">New Folder</h2>
          <button className="btn-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="modal-body">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="form-group">
              <label className="form-label">Folder name</label>
              <input
                type="text"
                id="new-folder-name"
                required
                autoComplete="off"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="form-input"
                placeholder="My folder"
              />
            </div>
          </form>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" form="new-folder-form" className="btn-primary">
            <Plus size={16} /> Create
          </button>
        </div>
      </div>
    </div>
  );
}

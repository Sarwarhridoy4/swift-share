import React, { useState } from 'react';
import { Lock, X, Copy, Share2 } from 'lucide-react';

interface ShareModalProps {
  open: boolean;
  onClose: () => void;
  path: string;
  expiresIn: number;
  onCreate: (expiresIn: number, password?: string) => void;
  onCopyLink: () => void;
  link: string;
}

export default function ShareModal({ open, onClose, path, expiresIn, onCreate, onCopyLink, link }: ShareModalProps) {
  const [password, setPassword] = useState('');
  const [showResult, setShowResult] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCreate(expiresIn, password || undefined);
    setShowResult(true);
  };

  if (!open) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-backdrop" onClick={onClose} />
      <div className="modal">
        <div className="modal-header">
          <h2 className="modal-title">Share File</h2>
          <button className="btn-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="modal-body">
          {!showResult ? (
            <form onSubmit={handleSubmit} className="space-y-5">
              <input type="hidden" id="share-path" defaultValue={path} />
              <div className="form-group">
                <label className="form-label">Expires in (hours)</label>
                <input
                  type="number"
                  id="share-expiry"
                  defaultValue={expiresIn}
                  min="1"
                  max="720"
                  className="form-input"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Password (optional)</label>
                <input
                  type="password"
                  id="share-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Leave empty for no password"
                  className="form-input"
                />
              </div>
            </form>
          ) : (
            <div className="space-y-3">
              <div className="form-group">
                <label className="form-label">Share Link</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    id="share-link"
                    readOnly
                    defaultValue={link}
                    className="flex-1 form-input text-sm"
                  />
                  <button
                    type="button"
                    className="btn-ghost shrink-0"
                    onClick={onCopyLink}
                  >
                    <Copy size={16} /> Copy
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button type="button" className="btn-ghost" onClick={onClose}>Cancel</button>
          {!showResult ? (
            <button type="submit" form="share-form" className="btn-primary">
              <Share2 size={16} /> Create Share
            </button>
          ) : (
            <button type="button" className="btn-ghost" onClick={onClose}>Done</button>
          )}
        </div>
      </div>
    </div>
  );
}

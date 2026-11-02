import React from 'react';
import { QrCode as QrIcon, X } from 'lucide-react';

interface QRModalProps {
  open: boolean;
  onClose: () => void;
  qrUrl: string;
}

export default function QRModal({ open, onClose, qrUrl }: QRModalProps) {
  if (!open) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-backdrop" onClick={onClose} />
      <div className="modal">
        <div className="modal-header">
          <h2 className="modal-title">Connect from mobile</h2>
          <button className="btn-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="modal-body">
          <p className="qr-subtitle">Scan to open SwiftShare on your phone</p>
          <div className="qr-card">
            <canvas id="qrCanvas" className="qr-canvas" width={220} height={220} />
            <div className="qr-subtitle text-xs opacity-70">SwiftShare</div>
          </div>
          <input
            type="text"
            id="qr-url"
            readOnly
            defaultValue={qrUrl}
            className="w-full form-input text-center text-sm"
          />
        </div>
        <div className="modal-footer">
          <button className="btn-close" onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  );
}

import React from 'react';

interface TransferPanelProps {
  transfer: { name: string; loaded: number; total: number; percent: number } | null;
  onCancel: () => void;
}

export default function TransferPanel({ transfer, onCancel }: TransferPanelProps) {
  if (!transfer) return null;

  return (
    <div className="transfer-panel">
      <div className="transfer-header">
        <span className="transfer-name">{transfer.name}</span>
        <span className="transfer-percent">{transfer.percent}%</span>
      </div>
      <div className="transfer-progress">
        <div className="transfer-bar" style={{ width: `${transfer.percent}%` }}></div>
      </div>
      <div className="transfer-meta">
        {formatSize(transfer.loaded)} / {formatSize(transfer.total)}
      </div>
    </div>
  );
}

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

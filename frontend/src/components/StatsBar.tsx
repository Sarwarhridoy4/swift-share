import React from 'react';
import { formatSize } from '@/lib/utils';

interface StatsBarProps {
  files: number;
  folders: number;
  size: number;
  shares: number;
}

export default function StatsBar({ files, folders, size, shares }: StatsBarProps) {
  return (
    <div className="stats-bar">
      <div className="stat-card">
        <div className="stat-value">{files}</div>
        <div className="stat-label">Files</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{folders}</div>
        <div className="stat-label">Folders</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{formatSize(size)}</div>
        <div className="stat-label">Total Size</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{shares}</div>
        <div className="stat-label">Active Shares</div>
      </div>
    </div>
  );
}

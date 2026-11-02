import React from 'react';
import { Sun, Moon, Smartphone, Link } from 'lucide-react';

interface HeaderProps {
  theme: string;
  toggleTheme: () => void;
  connectionInfo: { ip: string; port: number } | null;
  qrUrl: string;
  onOpenQR: () => void;
}

export default function Header({ theme, toggleTheme, connectionInfo, qrUrl, onOpenQR }: HeaderProps) {
  const url = connectionInfo ? `http://${connectionInfo.ip}:${connectionInfo.port}` : 'Loading...';

  return (
    <header className="app-header">
      <div className="px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-linear-to-r from-brand-600 to-accent-600 shadow-lg shadow-brand">
            <span className="text-xl">📁</span>
          </div>
          <div>
            <h1 className="font-bold text-slate-800 dark:text-slate-100 tracking-tight">SwiftShare</h1>
            <p className="text-[10px] text-slate-400 dark:text-slate-500 uppercase tracking-wider">Local file sharing</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-ghost" onClick={onOpenQR} title="QR code for mobile">
            <Smartphone className="text-lg" />
          </button>
          <button className="btn-ghost" onClick={toggleTheme} title="Toggle theme">
            {theme === 'dark' ? <Sun className="text-lg" /> : <Moon className="text-lg" />}
          </button>
        </div>
      </div>
      <div className="px-4 pb-3 connection-chip">
        <span className="h-2 w-2 rounded-full bg-success-500 animate-[pulse_2s_cubic-bezier(0.4,0,0.6,1)_infinite]" aria-hidden="true"></span>
        <span className="text-slate-500 dark:text-slate-400">Reachable at</span>
        <span className="font-semibold text-brand-600 dark:text-brand-400 truncate max-w-xs" title={url}>{url}</span>
      </div>
    </header>
  );
}

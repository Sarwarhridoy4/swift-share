import React from 'react';
import { Home } from 'lucide-react';

interface BreadcrumbProps {
  currentPath: string;
  onNavigate: (path: string) => void;
}

export default function Breadcrumb({ currentPath, onNavigate }: BreadcrumbProps) {
  const parts = currentPath ? currentPath.split('/').filter(Boolean) : [];

  return (
    <nav className="breadcrumb" aria-label="Breadcrumb">
      <button className="breadcrumb-item" onClick={() => onNavigate('')}>
        <Home size={14} className="mr-1" /> Home
      </button>
      {parts.map((part, i) => {
        const current = parts.slice(0, i + 1).join('/');
        return (
          <React.Fragment key={i}>
            <span className="breadcrumb-separator">/</span>
            <button className="breadcrumb-item" onClick={() => onNavigate(current)}>
              {part}
            </button>
          </React.Fragment>
        );
      })}
    </nav>
  );
}

import React from 'react';

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error';
}

interface ToastContainerProps {
  toasts: Toast[];
}

export default function ToastContainer({ toasts }: ToastContainerProps) {
  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast ${toast.type}`} role="alert" aria-live="polite">
          {toast.type === 'success' ? '✅' : '❌'}
          {toast.message}
        </div>
      ))}
    </div>
  );
}

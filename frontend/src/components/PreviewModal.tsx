import React from 'react';
import { FileText, Image, Video, Music, Download, X } from 'lucide-react';

interface PreviewModalProps {
  open: boolean;
  onClose: () => void;
  path: string;
}

export default function PreviewModal({ open, onClose, path }: PreviewModalProps) {
  if (!open) return null;

  const mime = path ? path.split('.').pop()?.toLowerCase() : '';
  const isImage = ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(mime || '');
  const isVideo = ['mp4', 'mov', 'avi', 'mkv'].includes(mime || '');
  const isAudio = ['mp3', 'wav', 'flac'].includes(mime || '');
  const isPdf = mime === 'pdf';

  const downloadUrl = `${window.location.origin}/api/files/download?path=${encodeURIComponent(path)}`;

  const iconMap: Record<string, React.ReactNode> = {
    jpg: <Image size={48} />,
    jpeg: <Image size={48} />,
    png: <Image size={48} />,
    gif: <Image size={48} />,
    svg: <Image size={48} />,
    webp: <Image size={48} />,
    mp4: <Video size={48} />,
    mov: <Video size={48} />,
    avi: <Video size={48} />,
    mkv: <Video size={48} />,
    mp3: <Music size={48} />,
    wav: <Music size={48} />,
    flac: <Music size={48} />,
    pdf: <FileText size={48} />,
  };

  return (
    <div className="modal-overlay">
      <div className="modal-backdrop" onClick={onClose} />
      <div className="modal" style={{ maxWidth: '720px' }}>
        <div className="modal-header">
          <h2 className="modal-title">File Preview</h2>
          <button className="btn-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="modal-body">
          <div className="max-h-[70vh] overflow-auto">
            {isImage ? (
              <img src={downloadUrl} className="max-w-full max-h-[70vh] rounded-xl shadow-lg" alt="Preview" />
            ) : isVideo ? (
              <video src={downloadUrl} controls className="max-w-full max-h-[70vh] rounded-xl shadow-lg"></video>
            ) : isAudio ? (
              <audio src={downloadUrl} controls className="w-full"></audio>
            ) : isPdf ? (
              <iframe src={downloadUrl} className="w-full h-[70vh] rounded-xl shadow-lg border-0" title="PDF preview"></iframe>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <div className="text-6xl mb-4 opacity-40">{iconMap[mime || ''] || <FileText size={48} />}</div>
                <p className="text-slate-500 dark:text-slate-400 mb-6">Preview not available for this file type</p>
                <a href={downloadUrl} download className="btn-primary">
                  <Download size={16} className="mr-2" /> Download to view
                </a>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

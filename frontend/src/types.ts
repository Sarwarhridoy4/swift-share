export type FileItem = {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  modified: string;
  mime_type?: string;
};

export type Theme = 'light' | 'dark';


export type TransferStatus = 'in_progress' | 'completed' | 'error';

export type TransferProgress = {
  transfer_id: string;
  filename: string;
  total: number;
  loaded: number;
  percent: number;
  status: TransferStatus;
  error?: string;
};

export type ShareInfo = {
  id: string;
  path: string;
  created_at: string;
  expires_at: string;
  download_count: number;
  password_protected: boolean;
};

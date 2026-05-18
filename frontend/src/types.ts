export interface LoginResponse {
  success: boolean;
  token: string;
}

export interface ApiError {
  detail?: string;
  error?: string;
  message?: string;
}

export interface TaskStatus {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | string;
  logs: string[];
  elapsed_time?: number;
  error?: string;
}

export interface ActiveTask {
  has_active: boolean;
  task_id?: string;
  stage?: string;
  started_at?: string;
  logs?: string[];
}

export interface HistoryRecord {
  id: string;
  timestamp: string;
  status: string;
  work_dir: string;
  file_count: number;
  elapsed_time: number;
  error?: string | null;
  result_tables: string[];
}

export interface HistoryDetail extends HistoryRecord {
  logs: string[];
}

export interface CacheSize {
  success: boolean;
  size_bytes: number;
  size_formatted: string;
  file_count: number;
  dir_count: number;
}

export interface AppConfig {
  update: string;
  mysql: {
    host: string;
    port: number;
    user: string;
    passwd?: string;
    dbname: string;
  };
  remote_data: RemoteDataConfig;
  sheet_filter: string[];
  extract_fields: Array<Record<string, unknown>>;
}

export interface RemoteDataConfig {
  enabled: boolean;
  protocol: 'ftp' | 'sftp';
  host: string;
  port: number;
  user: string;
  passwd?: string;
  remote_dir: string;
  passive: boolean;
  timeout: number;
}

export interface TableInfo {
  name: string;
  columns: Array<{
    Field?: string;
    Type?: string;
    Null?: string;
    Key?: string;
    Default?: unknown;
    Extra?: string;
    [key: string]: unknown;
  }>;
  row_count: number;
}

export interface TableData {
  data: Array<Record<string, unknown>>;
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ScriptContent {
  success: boolean;
  content: string;
  modified: string | null;
  path: string;
  error?: string;
}

export interface DatabaseInfo {
  success: boolean;
  version?: string;
  load_data_infile?: boolean;
  load_data_message?: string;
  error?: string;
}

export interface ServiceStatus {
  status: string;
  version: string;
  platform: string;
  supervisor: boolean;
  container: boolean;
  pid: number;
  python_version: string;
}

export interface ApiMessage {
  success: boolean;
  message?: string;
  error?: string;
  update?: string;
  task_id?: string;
}

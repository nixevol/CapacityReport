export interface LoginResponse {
  success: boolean;
  token: string;
}

export interface ApiError {
  detail?: string | ApiErrorDetail;
  error?: string;
  message?: string;
  code?: string;
}

export interface ApiErrorDetail {
  code?: string;
  message?: string;
  expires_on?: string;
  current_date?: string;
  key_label?: string;
  [key: string]: unknown;
}

export interface LicenseStatus {
  success: boolean;
  expires_on: string;
  key_label: string;
  current_date?: string | null;
  zip_count?: number;
}

export interface TaskStatus {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | string;
  stage?: string | null;
  logs: string[];
  elapsed_time?: number;
  error?: string;
  error_detail?: ApiErrorDetail;
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
  history_retention: HistoryRetentionConfig;
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
  auto_delete_source: boolean;
}

export interface HistoryRetentionConfig {
  enabled: boolean;
  keep_count: number;
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

export interface ApiMessage {
  success: boolean;
  message?: string;
  error?: string;
  update?: string;
  task_id?: string;
}

export interface ApiTokenRecord {
  id: string;
  name: string;
  prefix: string;
  suffix: string;
  token?: string | null;
  token_available?: boolean;
  created_at: string;
  expires_at: string | null;
  enabled: boolean;
  expired: boolean;
  last_used_at?: string | null;
  last_used_from?: string | null;
}

export interface ApiTokenListResponse {
  success: boolean;
  tokens: ApiTokenRecord[];
}

export interface ApiTokenMutationResponse {
  success: boolean;
  message?: string;
  token?: string;
  record: ApiTokenRecord;
}

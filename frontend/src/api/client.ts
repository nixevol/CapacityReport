import type { ApiError, ApiErrorDetail } from '../types';

const TOKEN_KEY = 'capacity_report_token';
const DESKTOP_API_BASE = 'http://127.0.0.1:9081';
const API_BASE = resolveApiBase();
const API_FETCH_RETRIES = 8;
const API_FETCH_RETRY_DELAY_MS = 500;
const TAURI_HTTP_ERROR_PREFIX = 'CAPAREPORT_HTTP_ERROR:';
let onUnauthorized: (() => void) | null = null;
let cachedTauriInvoke: TauriInvoke | null = null;

type TauriInvoke = <T>(command: string, args?: Record<string, unknown>) => Promise<T>;

export interface DownloadResult {
  saved: boolean;
  path?: string;
}

interface TauriDownloadHeader {
  name: string;
  value: string;
}

interface TauriDownloadRequest {
  url: string;
  method: 'GET' | 'POST';
  filename: string;
  headers: TauriDownloadHeader[];
  body?: string;
}

interface TauriDownloadResult {
  saved: boolean;
  path?: string;
}

export class ApiRequestError extends Error {
  status: number;
  code?: string;
  detail?: ApiErrorDetail;

  constructor(message: string, status: number, detail?: ApiErrorDetail) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
    this.code = detail?.code;
    this.detail = detail;
  }
}

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || '';
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  document.cookie = `token=${token}; path=/; max-age=${60 * 60 * 24 * 30}`;
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  document.cookie = 'token=; path=/; max-age=0';
}

export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

export async function apiGet<T>(url: string): Promise<T> {
  return request<T>(url, { method: 'GET' });
}

export async function apiPost<T>(url: string, body?: unknown): Promise<T> {
  return request<T>(url, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' }
  });
}

export async function request<T>(url: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = isLoginRequest(url) ? '' : getToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetchWithRetry(apiUrl(url), { ...init, headers });
  if (response.status === 401) {
    if (isLoginRequest(url)) {
      const error = await readError(response);
      throw new ApiRequestError(error.message, response.status, error.detail);
    }

    clearToken();
    onUnauthorized?.();
    throw new ApiRequestError('登录已过期，请重新登录', response.status, {
      code: 'UNAUTHORIZED',
      message: '登录已过期，请重新登录'
    });
  }

  if (!response.ok) {
    const error = await readError(response);
    throw new ApiRequestError(error.message, response.status, error.detail);
  }

  return response.json() as Promise<T>;
}

export function upload<T>(
  url: string,
  formData: FormData,
  onProgress?: (percent: number) => void
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', apiUrl(url));

    const token = getToken();
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    xhr.upload.addEventListener('progress', event => {
      if (event.lengthComputable) {
        onProgress?.(Math.round((event.loaded / event.total) * 100));
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status === 401) {
        clearToken();
        onUnauthorized?.();
        reject(
          new ApiRequestError('登录已过期，请重新登录', xhr.status, {
            code: 'UNAUTHORIZED',
            message: '登录已过期，请重新登录'
          })
        );
        return;
      }

      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new Error(parseXhrError(xhr.responseText)));
        return;
      }

      resolve(JSON.parse(xhr.responseText) as T);
    });

    xhr.addEventListener('error', () => reject(new Error('网络错误')));
    xhr.send(formData);
  });
}

export async function download(url: string, body: unknown, filename: string): Promise<DownloadResult> {
  const headers = new Headers({ 'Content-Type': 'application/json' });
  const token = getToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (isTauriRuntime()) {
    return await downloadWithTauri({
      url: apiUrl(url),
      method: 'POST',
      filename,
      headers: headersToPairs(headers),
      body: JSON.stringify(body)
    });
  }

  const response = await fetchWithRetry(apiUrl(url), {
    method: 'POST',
    headers,
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    const error = await readError(response);
    throw new ApiRequestError(error.message, response.status, error.detail);
  }

  return await saveBlobResponse(response, parseFilename(response.headers.get('content-disposition')) || filename);
}

export async function downloadGet(url: string, fallbackFilename: string): Promise<DownloadResult> {
  const headers = new Headers();
  const token = getToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (isTauriRuntime()) {
    return await downloadWithTauri({
      url: apiUrl(url),
      method: 'GET',
      filename: fallbackFilename,
      headers: headersToPairs(headers)
    });
  }

  const response = await fetchWithRetry(apiUrl(url), { headers });
  if (response.status === 401) {
    clearToken();
    onUnauthorized?.();
    throw new ApiRequestError('登录已过期，请重新登录', response.status, {
      code: 'UNAUTHORIZED',
      message: '登录已过期，请重新登录'
    });
  }

  if (!response.ok) {
    const error = await readError(response);
    throw new ApiRequestError(error.message, response.status, error.detail);
  }

  const filename = parseFilename(response.headers.get('content-disposition')) || fallbackFilename;
  return await saveBlobResponse(response, filename);
}

async function readError(response: Response): Promise<{ message: string; detail?: ApiErrorDetail }> {
  try {
    const data = (await response.json()) as ApiError;
    return parseApiError(data, response.statusText);
  } catch {
    return { message: response.statusText || '请求失败' };
  }
}

function parseXhrError(text: string): string {
  try {
    const data = JSON.parse(text) as ApiError;
    return parseApiError(data, '请求失败').message;
  } catch {
    return text || '请求失败';
  }
}

function parseApiError(data: ApiError, fallback: string): { message: string; detail?: ApiErrorDetail } {
  if (typeof data.detail === 'object' && data.detail !== null) {
    return {
      message: data.detail.message || data.message || data.error || fallback,
      detail: data.detail
    };
  }

  return {
    message: data.detail || data.error || data.message || fallback,
    detail: data.code ? { code: data.code, message: data.message || data.error } : undefined
  };
}

async function saveBlobResponse(response: Response, filename: string): Promise<DownloadResult> {
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(objectUrl);
  return { saved: true };
}

async function downloadWithTauri(request: TauriDownloadRequest): Promise<DownloadResult> {
  try {
    const invoke = await getTauriInvoke();
    const result = await invoke<TauriDownloadResult>('download_to_file', { request });
    return { saved: result.saved, path: result.path };
  } catch (error) {
    throw parseTauriDownloadError(error);
  }
}

export async function openPathInFileManager(path: string): Promise<void> {
  if (!isTauriRuntime()) return;
  const invoke = await getTauriInvoke();
  await invoke('open_path_in_file_manager', { path });
}

async function getTauriInvoke(): Promise<TauriInvoke> {
  if (!cachedTauriInvoke) {
    const api = await import('@tauri-apps/api/core');
    cachedTauriInvoke = api.invoke;
  }
  return cachedTauriInvoke;
}

function headersToPairs(headers: Headers): TauriDownloadHeader[] {
  const pairs: TauriDownloadHeader[] = [];
  headers.forEach((value, name) => {
    pairs.push({ name, value });
  });
  return pairs;
}

function parseTauriDownloadError(error: unknown): Error {
  const message = error instanceof Error ? error.message : String(error || '下载失败');
  if (!message.startsWith(TAURI_HTTP_ERROR_PREFIX)) {
    return error instanceof Error ? error : new Error(message);
  }

  const payload = message.slice(TAURI_HTTP_ERROR_PREFIX.length);
  const separator = payload.indexOf(':');
  const status = Number(payload.slice(0, separator));
  const body = separator >= 0 ? payload.slice(separator + 1) : '';
  const parsed = parseApiErrorText(body, `下载失败 (${status || 'HTTP'})`);

  if (status === 401) {
    clearToken();
    onUnauthorized?.();
  }

  return new ApiRequestError(parsed.message, status || 500, parsed.detail);
}

function parseApiErrorText(text: string, fallback: string): { message: string; detail?: ApiErrorDetail } {
  try {
    const data = JSON.parse(text) as ApiError;
    return parseApiError(data, fallback);
  } catch {
    return { message: text || fallback };
  }
}

async function fetchWithRetry(url: string, init: RequestInit): Promise<Response> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= API_FETCH_RETRIES; attempt += 1) {
    try {
      return await fetch(url, init);
    } catch (error) {
      lastError = error;
      if (attempt === API_FETCH_RETRIES) {
        break;
      }
      await sleep(API_FETCH_RETRY_DELAY_MS);
    }
  }

  throw lastError instanceof Error ? lastError : new Error('网络请求失败');
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => window.setTimeout(resolve, ms));
}

function parseFilename(disposition: string | null): string {
  if (!disposition) return '';

  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
  return plainMatch?.[1] || '';
}

function apiUrl(url: string): string {
  if (!API_BASE || /^https?:\/\//i.test(url)) {
    return url;
  }
  return `${API_BASE}${url.startsWith('/') ? url : `/${url}`}`;
}

function resolveApiBase(): string {
  const configured = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');
  if (configured) {
    return configured;
  }
  return isTauriRuntime() ? DESKTOP_API_BASE : '';
}

function isTauriRuntime(): boolean {
  const win = window as Window & {
    __TAURI__?: unknown;
    __TAURI_INTERNALS__?: unknown;
  };
  return Boolean(win.__TAURI__ || win.__TAURI_INTERNALS__ || navigator.userAgent.includes('Tauri'));
}

function isLoginRequest(url: string): boolean {
  try {
    const parsed = new URL(url, window.location.origin);
    return parsed.pathname === '/api/login';
  } catch {
    return url.replace(/^https?:\/\/[^/]+/i, '').split('?')[0] === '/api/login';
  }
}

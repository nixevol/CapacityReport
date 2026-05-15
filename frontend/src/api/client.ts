import type { ApiError } from '../types';

const TOKEN_KEY = 'capacity_report_token';
let onUnauthorized: (() => void) | null = null;

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
  const token = getToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, { ...init, headers });
  if (response.status === 401) {
    clearToken();
    onUnauthorized?.();
    throw new Error('登录已过期，请重新登录');
  }

  if (!response.ok) {
    const message = await readError(response);
    throw new Error(message);
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
    xhr.open('POST', url);

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
        reject(new Error('登录已过期，请重新登录'));
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

export async function download(url: string, body: unknown, filename: string): Promise<void> {
  const headers = new Headers({ 'Content-Type': 'application/json' });
  const token = getToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  await saveBlobResponse(response, filename);
}

export async function downloadGet(url: string, fallbackFilename: string): Promise<void> {
  const headers = new Headers();
  const token = getToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, { headers });
  if (response.status === 401) {
    clearToken();
    onUnauthorized?.();
    throw new Error('登录已过期，请重新登录');
  }

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  const filename = parseFilename(response.headers.get('content-disposition')) || fallbackFilename;
  await saveBlobResponse(response, filename);
}

async function readError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as ApiError;
    return data.detail || data.error || data.message || response.statusText;
  } catch {
    return response.statusText || '请求失败';
  }
}

function parseXhrError(text: string): string {
  try {
    const data = JSON.parse(text) as ApiError;
    return data.detail || data.error || data.message || '请求失败';
  } catch {
    return text || '请求失败';
  }
}

async function saveBlobResponse(response: Response, filename: string): Promise<void> {
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(objectUrl);
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

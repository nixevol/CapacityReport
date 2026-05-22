export type LogLevel = 'default' | 'info' | 'success' | 'warning' | 'error';

export interface ColoredLogLine {
  text: string;
  level: LogLevel;
}

export function toColoredLogLines(text: string, fallback = '暂无日志'): ColoredLogLine[] {
  const lines = text ? text.split(/\r?\n/) : [fallback];
  return lines.map(line => ({
    text: line,
    level: resolveLogLevel(line)
  }));
}

export function resolveLogLevel(line: string): LogLevel {
  const marker = line.match(/\[(ERROR|WARN|WARNING|SUCCESS|INFO)\]/i)?.[1]?.toUpperCase();
  if (marker === 'ERROR') return 'error';
  if (marker === 'WARN' || marker === 'WARNING') return 'warning';
  if (marker === 'SUCCESS') return 'success';
  if (marker === 'INFO') return 'info';
  if (/\b(ERROR|FAILED|FAILURE)\b|错误|失败/i.test(line)) return 'error';
  if (/\b(WARN|WARNING)\b|警告/i.test(line)) return 'warning';
  if (/\b(SUCCESS|SUCCEEDED|COMPLETED)\b|成功|已完成|处理完成|下载完成|执行完成/i.test(line)) {
    return 'success';
  }
  return 'default';
}

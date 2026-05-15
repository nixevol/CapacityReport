import { shallowReactive, unref, type Ref } from 'vue';

type HeaderValue<T> = T | Ref<T> | (() => T);

export interface PageHeaderAction {
  key: string;
  label: HeaderValue<string>;
  icon?: HeaderValue<string>;
  title?: HeaderValue<string>;
  kind?: 'button' | 'text';
  type?: 'default' | 'primary' | 'success' | 'warning' | 'error';
  variant?: 'solid' | 'outline' | 'text';
  loading?: HeaderValue<boolean>;
  disabled?: HeaderValue<boolean>;
  onClick?: () => void | Promise<void>;
}

export const pageHeader = shallowReactive<{
  subtitle: HeaderValue<string> | '';
  actions: PageHeaderAction[];
}>({
  subtitle: '',
  actions: []
});

export function setPageHeader(config: { subtitle?: HeaderValue<string>; actions?: PageHeaderAction[] }) {
  pageHeader.subtitle = config.subtitle || '';
  pageHeader.actions = config.actions || [];
}

export function resetPageHeader() {
  pageHeader.subtitle = '';
  pageHeader.actions = [];
}

export function resolveHeaderValue<T>(value: HeaderValue<T> | undefined, fallback: T): T {
  if (typeof value === 'function') {
    return (value as () => T)();
  }
  return value === undefined ? fallback : unref(value);
}

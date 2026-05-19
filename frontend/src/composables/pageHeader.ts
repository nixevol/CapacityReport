import { shallowReactive, unref, type Component, type Ref } from 'vue';
import type { DropdownOption } from 'naive-ui';

type HeaderValue<T> = T | Ref<T> | (() => T);

export interface PageHeaderAction {
  key: string;
  label: HeaderValue<string>;
  icon?: HeaderValue<Component>;
  title?: HeaderValue<string>;
  kind?: 'button' | 'text';
  type?: 'default' | 'primary' | 'success' | 'warning' | 'error';
  variant?: 'solid' | 'outline' | 'text';
  loading?: HeaderValue<boolean>;
  disabled?: HeaderValue<boolean>;
  dropdownOptions?: HeaderValue<DropdownOption[]>;
  onClick?: () => void | Promise<void>;
  onSelect?: (key: string | number, option: DropdownOption) => void | Promise<void>;
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

export function resolveHeaderValue<T>(value: HeaderValue<T> | undefined): T | undefined;
export function resolveHeaderValue<T>(value: HeaderValue<T> | undefined, fallback: T): T;
export function resolveHeaderValue<T>(value: HeaderValue<T> | undefined, fallback?: T): T | undefined {
  if (typeof value === 'function') {
    return (value as () => T)();
  }
  return value === undefined ? fallback : unref(value);
}

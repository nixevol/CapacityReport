import { ref } from 'vue';

export type AppTheme = 'light' | 'dark';

const THEME_KEY = 'theme';

export const themeName = ref<AppTheme>(readStoredTheme());

applyTheme(themeName.value);

export function setAppTheme(nextTheme: AppTheme) {
  themeName.value = nextTheme;
  applyTheme(nextTheme);
}

export function toggleAppTheme() {
  setAppTheme(themeName.value === 'dark' ? 'light' : 'dark');
}

function readStoredTheme(): AppTheme {
  try {
    const stored = typeof localStorage === 'undefined' ? null : localStorage.getItem(THEME_KEY);
    return stored === 'dark' ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

function applyTheme(nextTheme: AppTheme) {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', nextTheme);
  }
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(THEME_KEY, nextTheme);
    }
  } catch {
    // Ignore storage failures so theme switching never blocks the UI.
  }
}

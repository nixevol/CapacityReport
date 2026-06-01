import { createApp } from 'vue';

import App from './App.vue';
import { router } from './router';
import './styles.css';

if (isTauriRuntime()) {
  window.addEventListener('contextmenu', event => event.preventDefault());
  window.addEventListener('keydown', event => {
    if (event.key === 'F12' || (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === 'i')) {
      event.preventDefault();
    }
  });
}

createApp(App).use(router).mount('#app');

function isTauriRuntime(): boolean {
  const win = window as Window & {
    __TAURI__?: unknown;
    __TAURI_INTERNALS__?: unknown;
  };
  return Boolean(win.__TAURI__ || win.__TAURI_INTERNALS__ || navigator.userAgent.includes('Tauri'));
}

<template>
  <LoginView v-if="!token" :loading="loginLoading" @login="handleLogin" />
  <n-layout v-else has-sider class="app-layout">
    <n-layout-sider
      class="app-sider"
      collapse-mode="width"
      :collapsed="sidebarCollapsed"
      :collapsed-width="64"
      :width="220"
      show-trigger="arrow-circle"
      @update:collapsed="handleSidebarCollapsed"
    >
      <div class="brand">
        <div class="brand-mark">📊</div>
        <div class="brand-text">CapacityReport</div>
      </div>
      <n-menu
        :value="activeMenu"
        class="app-menu"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        @update:value="handleMenuChange"
      />
      <div class="sider-footer">
        <span class="sider-version">
          <span class="sider-version-label">版本：</span>
          <span class="sider-version-number">v2.0.2</span>
        </span>
        <span class="sider-powered">Power by：NIXEVOL</span>
      </div>
    </n-layout-sider>

    <n-layout>
      <n-layout-header bordered class="topbar page-header">
        <div class="page-header-content">
          <h1>{{ currentTitle }}</h1>
          <span v-if="pageSubtitle" class="page-subtitle" :title="pageSubtitle">{{ pageSubtitle }}</span>
        </div>
        <div class="page-header-actions">
          <template v-for="action in pageHeader.actions" :key="action.key">
            <span v-if="action.kind === 'text'" class="header-info-text">
              {{ actionLabel(action) }}
            </span>
            <n-button
              v-else
              size="small"
              :type="action.type === 'default' ? undefined : action.type"
              :tertiary="action.variant !== 'solid'"
              :text="action.variant === 'text'"
              :loading="actionLoading(action)"
              :disabled="actionDisabled(action)"
              :title="actionTitle(action)"
              @click="runHeaderAction(action)"
            >
              <template v-if="actionIcon(action)" #icon>
                <n-icon><component :is="actionIcon(action)" /></n-icon>
              </template>
              {{ actionLabel(action) }}
            </n-button>
          </template>

          <button class="theme-toggle" type="button" :title="themeToggleTitle" @click="toggleTheme">
            <n-icon><component :is="themeToggleIcon" /></n-icon>
          </button>
          <button
            class="restart-btn"
            type="button"
            title="重启服务"
            :disabled="restarting"
            @click="restartService"
          >
            <n-icon><PowerOutline /></n-icon>
          </button>
          <n-button tertiary circle title="退出登录" class="logout-button" @click="logout">
            <template #icon>
              <n-icon><LogOutOutline /></n-icon>
            </template>
          </n-button>
        </div>
      </n-layout-header>

      <n-layout-content class="content">
        <RouterView />
      </n-layout-content>
    </n-layout>
  </n-layout>

  <div v-if="restarting" class="restart-overlay" role="status" aria-live="assertive">
    <div class="restart-overlay-content">
      <div class="restart-overlay-spinner"></div>
      <div class="restart-overlay-text">{{ restartOverlayText }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onBeforeUnmount, onMounted, ref, watch, type Component } from 'vue';
import { RouterView, useRoute, useRouter } from 'vue-router';
import { useDialog, useMessage, type MenuOption, NIcon } from 'naive-ui';
import {
  CloudUploadOutline,
  ConstructOutline,
  FileTrayFullOutline,
  LogOutOutline,
  MoonOutline,
  PowerOutline,
  ServerOutline,
  SettingsOutline,
  SunnyOutline
} from '@vicons/ionicons5';

import { apiGet, apiPost, clearToken, getToken, setToken, setUnauthorizedHandler } from './api/client';
import type { ApiMessage, LoginResponse, ServiceStatus } from './types';
import LoginView from './components/LoginView.vue';
import { pageHeader, resetPageHeader, resolveHeaderValue, type PageHeaderAction } from './composables/pageHeader';
import { themeName, toggleAppTheme } from './composables/theme';

const message = useMessage();
const dialog = useDialog();
const route = useRoute();
const router = useRouter();
const token = ref(getToken());
const loginLoading = ref(false);
const restarting = ref(false);
const restartOverlayText = ref('正在重启服务...');
const sidebarCollapsed = ref(localStorage.getItem('sidebarCollapsed') === 'true');
const menuKeys = ['workflow', 'history', 'database', 'script', 'settings'] as const;
type MenuKey = (typeof menuKeys)[number];
let restartPollTimer: number | undefined;

const menuOptions: MenuOption[] = [
  { label: '数据上传', key: 'workflow', icon: renderIcon(CloudUploadOutline) },
  { label: '处理历史', key: 'history', icon: renderIcon(FileTrayFullOutline) },
  { label: '数据管理', key: 'database', icon: renderIcon(ServerOutline) },
  { label: '脚本编辑', key: 'script', icon: renderIcon(ConstructOutline) },
  { label: '系统设置', key: 'settings', icon: renderIcon(SettingsOutline) }
];

const activeMenu = computed<MenuKey>(() => {
  return isMenuKey(route.name) ? route.name : 'workflow';
});

const currentTitle = computed(() => {
  return String(route.meta.title || menuOptions.find(item => item.key === activeMenu.value)?.label || '');
});
const pageSubtitle = computed(() => resolveHeaderValue(pageHeader.subtitle || '', ''));
const themeToggleIcon = computed<Component>(() => (themeName.value === 'dark' ? SunnyOutline : MoonOutline));
const themeToggleTitle = computed(() => (themeName.value === 'dark' ? '切换到浅色主题' : '切换到深色主题'));

onMounted(() => {
  window.addEventListener('dragover', preventWindowFileDrop, { capture: true });
  window.addEventListener('drop', preventWindowFileDrop, { capture: true });
});

onBeforeUnmount(() => {
  window.removeEventListener('dragover', preventWindowFileDrop, { capture: true });
  window.removeEventListener('drop', preventWindowFileDrop, { capture: true });
  if (restartPollTimer !== undefined) {
    window.clearTimeout(restartPollTimer);
  }
});

watch(
  () => route.name,
  () => resetPageHeader()
);

setUnauthorizedHandler(() => {
  token.value = '';
  message.warning('登录已过期');
});

async function handleLogin(payload: { username: string; password: string }) {
  loginLoading.value = true;
  try {
    const result = await apiPost<LoginResponse>('/api/login', payload);
    setToken(result.token);
    token.value = result.token;
    message.success('登录成功');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '登录失败');
  } finally {
    loginLoading.value = false;
  }
}

function logout() {
  clearToken();
  token.value = '';
}

function handleSidebarCollapsed(value: boolean) {
  sidebarCollapsed.value = value;
  localStorage.setItem('sidebarCollapsed', sidebarCollapsed.value ? 'true' : 'false');
}

function toggleTheme() {
  toggleAppTheme();
}

async function restartService() {
  if (restarting.value) return;

  dialog.warning({
    title: '重启服务',
    content: '确定要重启服务吗？这将中断当前所有操作。',
    positiveText: '重启',
    negativeText: '取消',
    onPositiveClick: () => {
      void executeRestartService();
    }
  });
}

async function executeRestartService() {
  restarting.value = true;
  restartOverlayText.value = '正在重启服务...';

  try {
    const result = await apiPost<ApiMessage>('/api/service/restart');
    restartOverlayText.value = result.message || '正在等待服务恢复...';
  } catch {
    restartOverlayText.value = '正在等待服务恢复...';
  }

  pollServiceStatus();
}

function pollServiceStatus() {
  let attempts = 0;
  const maxAttempts = 60;
  const pollInterval = 5000;

  const checkService = async () => {
    attempts += 1;

    try {
      await apiGet<ServiceStatus>('/api/service/status');
      restartOverlayText.value = '服务已恢复，正在刷新页面...';
      restartPollTimer = window.setTimeout(() => {
        window.location.reload();
      }, 500);
      return;
    } catch {
      restartOverlayText.value = `正在等待服务恢复... (${attempts}/${maxAttempts})`;
    }

    if (attempts < maxAttempts) {
      restartPollTimer = window.setTimeout(checkService, pollInterval);
      return;
    }

    restarting.value = false;
    restartOverlayText.value = '正在重启服务...';
    message.warning('服务重启超时，请手动刷新页面');
  };

  restartPollTimer = window.setTimeout(checkService, 3000);
}

function handleMenuChange(key: string | number) {
  if (!isMenuKey(key) || key === activeMenu.value) {
    return;
  }
  void router.push({ name: key });
}

function isMenuKey(value: unknown): value is MenuKey {
  return typeof value === 'string' && menuKeys.includes(value as MenuKey);
}

function renderIcon(icon: Component) {
  return () => h(NIcon, null, { default: () => h(icon) });
}

function actionLabel(action: PageHeaderAction) {
  return resolveHeaderValue(action.label, '');
}

function actionIcon(action: PageHeaderAction) {
  return resolveHeaderValue(action.icon) ?? null;
}

function actionTitle(action: PageHeaderAction) {
  return resolveHeaderValue(action.title, actionLabel(action));
}

function actionLoading(action: PageHeaderAction) {
  return resolveHeaderValue(action.loading, false);
}

function actionDisabled(action: PageHeaderAction) {
  return resolveHeaderValue(action.disabled, false);
}

function runHeaderAction(action: PageHeaderAction) {
  void action.onClick?.();
}

function preventWindowFileDrop(event: DragEvent) {
  const types = Array.from(event.dataTransfer?.types || []);
  if (!types.includes('Files')) {
    return;
  }
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'copy';
  }
}
</script>

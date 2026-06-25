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
        <div
          class="brand-mark"
          role="button"
          tabindex="0"
          title="CapacityReport"
          @click="handleBrandMarkClick"
          @keydown.enter.prevent="handleBrandMarkClick"
          @keydown.space.prevent="handleBrandMarkClick"
        >
          📊
        </div>
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
          <span class="sider-version-number">v3.0.0</span>
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
            <n-dropdown
              v-else-if="actionDropdownOptions(action).length"
              trigger="click"
              :options="actionDropdownOptions(action)"
              :disabled="actionDisabled(action)"
              :on-select="runHeaderActionSelect(action)"
            >
              <n-button
                size="small"
                :type="action.type === 'default' ? undefined : action.type"
                :tertiary="action.variant !== 'solid'"
                :text="action.variant === 'text'"
                :loading="actionLoading(action)"
                :disabled="actionDisabled(action)"
                :title="actionTitle(action)"
              >
                <template v-if="actionIcon(action)" #icon>
                  <n-icon><component :is="actionIcon(action)" /></n-icon>
                </template>
                <span class="header-dropdown-label">
                  <span>{{ actionLabel(action) }}</span>
                  <n-icon class="header-dropdown-caret"><ChevronDownOutline /></n-icon>
                </span>
              </n-button>
            </n-dropdown>
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

  <LicenseActivationModal v-if="licenseModalVisible" v-model:show="licenseModalVisible" @metrix-changed="onMetrixChanged" />
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, h, onBeforeUnmount, onMounted, ref, watch, type Component } from 'vue';
import { RouterView, useRoute, useRouter } from 'vue-router';
import { useMessage, type DropdownOption, type MenuOption, NIcon } from 'naive-ui';
import {
  ChevronDownOutline,
  CloudUploadOutline,
  ConstructOutline,
  FileTrayFullOutline,
  LogOutOutline,
  MoonOutline,
  ServerOutline,
  SettingsOutline,
  SunnyOutline
} from '@vicons/ionicons5';

import { apiGet, apiPost, clearToken, getToken, setToken, setUnauthorizedHandler } from './api/client';
import type { AppConfig, LoginResponse } from './types';
import { pageHeader, resetPageHeader, resolveHeaderValue, type PageHeaderAction } from './composables/pageHeader';
import { metrixEnabled } from './composables/metrixEnabled';
import { themeName, toggleAppTheme } from './composables/theme';

const LoginView = defineAsyncComponent(() => import('./components/LoginView.vue'));
const LicenseActivationModal = defineAsyncComponent(() => import('./components/LicenseActivationModal.vue'));
const message = useMessage();
const route = useRoute();
const router = useRouter();
const token = ref(getToken());
const loginLoading = ref(false);
const sidebarCollapsed = ref(localStorage.getItem('sidebarCollapsed') === 'true');
const licenseModalVisible = ref(false);
const brandClickCount = ref(0);
const menuKeys = ['workflow', 'history', 'database', 'script', 'settings'] as const;
type MenuKey = (typeof menuKeys)[number];
let brandClickResetTimer: number | undefined;

const menuOptions: MenuOption[] = [
  { label: '数据处理', key: 'workflow', icon: renderIcon(CloudUploadOutline) },
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
  if (token.value) {
    void loadMetrixEnabled();
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('dragover', preventWindowFileDrop, { capture: true });
  window.removeEventListener('drop', preventWindowFileDrop, { capture: true });
  if (brandClickResetTimer !== undefined) {
    window.clearTimeout(brandClickResetTimer);
  }
});

watch(
  () => route.name,
  () => resetPageHeader()
);

setUnauthorizedHandler(() => {
  token.value = '';
});

async function handleLogin(payload: { username: string; password: string }) {
  loginLoading.value = true;
  try {
    const result = await apiPost<LoginResponse>('/api/login', payload);
    setToken(result.token);
    token.value = result.token;
    message.success('登录成功');
    void loadMetrixEnabled();
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

function handleMenuChange(key: string | number) {
  if (!isMenuKey(key) || key === activeMenu.value) {
    return;
  }
  void router.push({ name: key });
}

function onMetrixChanged(enabled: boolean) {
  metrixEnabled.value = enabled;
}

async function loadMetrixEnabled() {
  try {
    const config = await apiGet<AppConfig>('/api/config/full');
    metrixEnabled.value = config.metrix_enabled ?? false;
  } catch {
    metrixEnabled.value = false;
  }
}

function handleBrandMarkClick() {
  brandClickCount.value += 1;
  if (brandClickResetTimer !== undefined) {
    window.clearTimeout(brandClickResetTimer);
  }

  if (brandClickCount.value >= 8) {
    brandClickCount.value = 0;
    licenseModalVisible.value = true;
    return;
  }

  brandClickResetTimer = window.setTimeout(() => {
    brandClickCount.value = 0;
  }, 2000);
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

function actionDropdownOptions(action: PageHeaderAction) {
  return resolveHeaderValue(action.dropdownOptions, []);
}

function runHeaderAction(action: PageHeaderAction) {
  void action.onClick?.();
}

function runHeaderActionSelect(action: PageHeaderAction) {
  return (key: string | number, option: DropdownOption) => {
    void action.onSelect?.(key, option);
  };
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

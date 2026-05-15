<template>
  <LoginView v-if="!token" :loading="loginLoading" @login="handleLogin" />
  <n-layout v-else has-sider class="app-layout">
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="224"
      show-trigger
    >
      <div class="brand">
        <div class="brand-mark">CR</div>
        <div class="brand-text">CapacityReport</div>
      </div>
      <n-menu
        v-model:value="activeMenu"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
      />
    </n-layout-sider>

    <n-layout>
      <n-layout-header bordered class="topbar">
        <div>
          <div class="page-title">{{ currentTitle }}</div>
          <div class="page-subtitle">容量报表处理与数据维护</div>
        </div>
        <n-space align="center">
          <n-tag size="small" type="success" round>已登录</n-tag>
          <n-button tertiary circle title="退出登录" @click="logout">
            <template #icon>
              <n-icon><LogOutOutline /></n-icon>
            </template>
          </n-button>
        </n-space>
      </n-layout-header>

      <n-layout-content class="content">
        <FileWorkflow v-if="activeMenu === 'workflow'" />
        <HistoryPanel v-else-if="activeMenu === 'history'" />
        <DatabasePanel v-else-if="activeMenu === 'database'" />
        <ScriptPanel v-else-if="activeMenu === 'script'" />
        <SettingsPanel v-else />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { computed, h, ref, type Component } from 'vue';
import { useMessage, type MenuOption, NIcon } from 'naive-ui';
import {
  CloudUploadOutline,
  ConstructOutline,
  FileTrayFullOutline,
  LogOutOutline,
  ServerOutline,
  SettingsOutline
} from '@vicons/ionicons5';

import { apiPost, clearToken, getToken, setToken, setUnauthorizedHandler } from './api/client';
import type { LoginResponse } from './types';
import LoginView from './components/LoginView.vue';
import FileWorkflow from './components/FileWorkflow.vue';
import HistoryPanel from './components/HistoryPanel.vue';
import DatabasePanel from './components/DatabasePanel.vue';
import ScriptPanel from './components/ScriptPanel.vue';
import SettingsPanel from './components/SettingsPanel.vue';

const message = useMessage();
const token = ref(getToken());
const activeMenu = ref('workflow');
const loginLoading = ref(false);

const menuOptions: MenuOption[] = [
  { label: '处理任务', key: 'workflow', icon: renderIcon(CloudUploadOutline) },
  { label: '处理历史', key: 'history', icon: renderIcon(FileTrayFullOutline) },
  { label: '数据表', key: 'database', icon: renderIcon(ServerOutline) },
  { label: 'SQL 脚本', key: 'script', icon: renderIcon(ConstructOutline) },
  { label: '系统设置', key: 'settings', icon: renderIcon(SettingsOutline) }
];

const currentTitle = computed(() => {
  return String(menuOptions.find(item => item.key === activeMenu.value)?.label || '');
});

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

function renderIcon(icon: Component) {
  return () => h(NIcon, null, { default: () => h(icon) });
}
</script>

<template>
  <n-grid :cols="12" :x-gap="16" :y-gap="16" responsive="screen">
    <n-gi :span="12" :m="8">
      <n-card title="SQL 脚本" size="small">
        <template #header-extra>
          <n-space>
            <n-button size="small" tertiary :loading="loading" @click="loadScript">重新加载</n-button>
            <n-button size="small" type="primary" :loading="saving" @click="saveScript">保存</n-button>
            <n-button size="small" type="warning" :loading="executing" @click="executeScript">执行</n-button>
          </n-space>
        </template>

        <n-space vertical>
          <n-alert v-if="scriptPath" type="default" :bordered="false">
            {{ scriptPath }} / 修改时间：{{ modified || '-' }}
          </n-alert>
          <n-input
            v-model:value="content"
            type="textarea"
            class="script-editor"
            :autosize="{ minRows: 24, maxRows: 32 }"
            spellcheck="false"
          />
        </n-space>
      </n-card>
    </n-gi>

    <n-gi :span="12" :m="4">
      <n-card title="执行状态" size="small">
        <template #header-extra>
          <n-button size="small" tertiary :disabled="!taskId" @click="refreshStatus">刷新</n-button>
        </template>

        <n-space vertical>
          <n-tag v-if="taskStatus" :type="statusType">{{ taskStatus.status }}</n-tag>
          <n-empty v-if="!taskStatus" description="脚本尚未执行" />
          <n-log v-else :log="logText" language="text" trim class="log-panel" />
        </n-space>
      </n-card>
    </n-gi>
  </n-grid>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useMessage } from 'naive-ui';

import { apiGet, apiPost } from '../api/client';
import type { ApiMessage, ScriptContent, TaskStatus } from '../types';

const message = useMessage();
const content = ref('');
const scriptPath = ref('');
const modified = ref<string | null>(null);
const loading = ref(false);
const saving = ref(false);
const executing = ref(false);
const taskId = ref('');
const taskStatus = ref<TaskStatus | null>(null);
let timer: number | undefined;

const logText = computed(() => taskStatus.value?.logs?.join('\n') || '等待执行日志');
const statusType = computed(() => {
  if (taskStatus.value?.status === 'completed') return 'success';
  if (taskStatus.value?.status === 'failed') return 'error';
  return 'info';
});

onMounted(() => {
  void loadScript();
});

onBeforeUnmount(() => {
  stopPolling();
});

async function loadScript() {
  loading.value = true;
  try {
    const result = await apiGet<ScriptContent>('/api/script/content');
    if (!result.success) {
      throw new Error(result.error || '加载脚本失败');
    }
    content.value = result.content;
    scriptPath.value = result.path;
    modified.value = result.modified;
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载脚本失败');
  } finally {
    loading.value = false;
  }
}

async function saveScript() {
  saving.value = true;
  try {
    const result = await apiPost<ApiMessage & { modified?: string }>('/api/script/save', {
      content: content.value
    });
    if (!result.success) {
      throw new Error(result.error || '保存失败');
    }
    modified.value = result.modified || modified.value;
    message.success(result.message || '保存成功');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存脚本失败');
  } finally {
    saving.value = false;
  }
}

async function executeScript() {
  executing.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/script/execute');
    if (!result.task_id) {
      throw new Error(result.message || '脚本任务启动失败');
    }
    taskId.value = result.task_id;
    taskStatus.value = { task_id: result.task_id, status: 'processing', logs: [] };
    message.success(result.message || '脚本任务已启动');
    startPolling();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '执行脚本失败');
  } finally {
    executing.value = false;
  }
}

function startPolling() {
  stopPolling();
  void refreshStatus();
  timer = window.setInterval(() => void refreshStatus(), 1500);
}

function stopPolling() {
  if (timer) {
    window.clearInterval(timer);
    timer = undefined;
  }
}

async function refreshStatus() {
  if (!taskId.value) return;
  try {
    taskStatus.value = await apiPost<TaskStatus>('/api/process/status', { task_id: taskId.value });
    if (['completed', 'failed'].includes(taskStatus.value.status)) {
      stopPolling();
    }
  } catch (error) {
    stopPolling();
    message.error(error instanceof Error ? error.message : '刷新执行状态失败');
  }
}
</script>

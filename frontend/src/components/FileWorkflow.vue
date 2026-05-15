<template>
  <n-grid :cols="12" :x-gap="16" :y-gap="16" responsive="screen">
    <n-gi :span="12" :m="5">
      <n-card title="文件上传" size="small">
        <n-space vertical size="large">
          <n-space>
            <n-button @click="fileInput?.click()">
              <template #icon><n-icon><DocumentAttachOutline /></n-icon></template>
              选择文件
            </n-button>
            <n-button @click="folderInput?.click()">
              <template #icon><n-icon><FolderOpenOutline /></n-icon></template>
              选择目录
            </n-button>
            <n-button tertiary :disabled="files.length === 0 || working" @click="clearFiles">
              清空
            </n-button>
          </n-space>

          <input ref="fileInput" class="hidden-input" type="file" multiple @change="pickFiles" />
          <input ref="folderInput" class="hidden-input" type="file" multiple @change="pickFiles" />

          <n-statistic label="待上传文件" :value="files.length" />
          <n-progress v-if="uploadProgress > 0" type="line" :percentage="uploadProgress" />

          <n-scrollbar class="file-list">
            <n-empty v-if="files.length === 0" description="未选择文件" />
            <n-list v-else bordered>
              <n-list-item v-for="item in files" :key="item.path">
                <n-thing :title="item.path" :description="formatBytes(item.file.size)" />
              </n-list-item>
            </n-list>
          </n-scrollbar>

          <n-button type="primary" block :disabled="files.length === 0" :loading="working" @click="uploadAndStart">
            上传并处理
          </n-button>
        </n-space>
      </n-card>
    </n-gi>

    <n-gi :span="12" :m="7">
      <n-card title="处理状态" size="small">
        <template #header-extra>
          <n-space>
            <n-tag v-if="taskStatus" :type="statusType">{{ taskStatus.status }}</n-tag>
            <n-button size="small" tertiary @click="checkActiveTask">刷新</n-button>
          </n-space>
        </template>

        <n-space vertical>
          <n-alert v-if="activeTask?.has_active" type="info" :bordered="false">
            当前任务：{{ activeTask.task_id }} / {{ activeTask.stage }}
          </n-alert>
          <n-alert v-if="taskStatus?.error" type="error" :bordered="false">
            {{ taskStatus.error }}
          </n-alert>
          <n-log :log="logText" language="text" trim class="log-panel" />
        </n-space>
      </n-card>
    </n-gi>
  </n-grid>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useMessage } from 'naive-ui';
import { DocumentAttachOutline, FolderOpenOutline } from '@vicons/ionicons5';

import { apiGet, apiPost, upload } from '../api/client';
import type { ActiveTask, TaskStatus } from '../types';

interface PickedFile {
  file: File;
  path: string;
}

interface UploadResponse {
  success: boolean;
  task_id: string;
  file_count: number;
}

const message = useMessage();
const fileInput = ref<HTMLInputElement | null>(null);
const folderInput = ref<HTMLInputElement | null>(null);
const files = ref<PickedFile[]>([]);
const uploadProgress = ref(0);
const working = ref(false);
const taskStatus = ref<TaskStatus | null>(null);
const activeTask = ref<ActiveTask | null>(null);
let timer: number | undefined;

const logText = computed(() => taskStatus.value?.logs?.join('\n') || '等待任务开始');
const statusType = computed(() => {
  if (taskStatus.value?.status === 'completed') return 'success';
  if (taskStatus.value?.status === 'failed') return 'error';
  return 'info';
});

onMounted(() => {
  const folder = folderInput.value as (HTMLInputElement & { webkitdirectory?: boolean }) | null;
  if (folder) {
    folder.webkitdirectory = true;
  }
  void checkActiveTask();
});

onBeforeUnmount(() => {
  stopPolling();
});

function pickFiles(event: Event) {
  const input = event.target as HTMLInputElement;
  const selected = Array.from(input.files || []);
  for (const file of selected) {
    const path = (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name;
    if (!files.value.some(item => item.path === path)) {
      files.value.push({ file, path });
    }
  }
  input.value = '';
}

function clearFiles() {
  files.value = [];
  uploadProgress.value = 0;
}

async function uploadAndStart() {
  const formData = new FormData();
  for (const item of files.value) {
    formData.append('files', item.file, item.path);
  }

  working.value = true;
  uploadProgress.value = 0;
  try {
    const result = await upload<UploadResponse>('/api/upload', formData, value => {
      uploadProgress.value = value;
    });
    message.success(`上传完成：${result.file_count} 个文件`);
    await apiPost('/api/process/start', { task_id: result.task_id });
    taskStatus.value = { task_id: result.task_id, status: 'processing', logs: [] };
    startPolling(result.task_id);
  } catch (error) {
    message.error(error instanceof Error ? error.message : '上传或启动任务失败');
  } finally {
    working.value = false;
  }
}

async function checkActiveTask() {
  try {
    activeTask.value = await apiGet<ActiveTask>('/api/task/status');
    if (activeTask.value.has_active && activeTask.value.task_id) {
      startPolling(activeTask.value.task_id);
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '获取任务状态失败');
  }
}

function startPolling(taskId: string) {
  stopPolling();
  void poll(taskId);
  timer = window.setInterval(() => void poll(taskId), 2000);
}

function stopPolling() {
  if (timer) {
    window.clearInterval(timer);
    timer = undefined;
  }
}

async function poll(taskId: string) {
  try {
    taskStatus.value = await apiPost<TaskStatus>('/api/process/status', { task_id: taskId });
    if (['completed', 'failed'].includes(taskStatus.value.status)) {
      stopPolling();
      await checkActiveTask();
    }
  } catch (error) {
    stopPolling();
    message.error(error instanceof Error ? error.message : '刷新任务状态失败');
  }
}

function formatBytes(size: number): string {
  if (size === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = size;
  for (const unit of units) {
    if (value < 1024) return `${value.toFixed(1)} ${unit}`;
    value /= 1024;
  }
  return `${value.toFixed(1)} TB`;
}
</script>

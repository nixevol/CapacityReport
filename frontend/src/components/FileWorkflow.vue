<template>
  <div class="upload-page-body">
    <section
      v-if="!taskInProgress"
      class="upload-zone"
      :class="{ dragover: isDragging, disabled: working }"
      role="button"
      tabindex="0"
      :aria-disabled="working"
      @click="openFilePicker"
      @keydown.enter.prevent="openFilePicker"
      @keydown.space.prevent="openFilePicker"
      @dragenter.prevent.stop="onDragEnter"
      @dragover.prevent.stop="onDragOver"
      @dragleave="onDragLeave"
      @drop.prevent.stop="onDrop"
    >
      <div class="upload-icon">
        <n-icon size="24"><FolderOpenOutline /></n-icon>
      </div>
      <h3>拖拽文件夹或文件到这里</h3>
      <p>支持 .zip, .xlsx, .xls, .csv 格式</p>
      <div class="upload-zone-actions">
        <span class="upload-hint">或者点击选择文件</span><br>
        <n-tooltip trigger="hover" placement="bottom">
          <template #trigger>
            <span class="remote-run-trigger" @click.stop @keydown.stop>
              <n-button
                type="primary"
                secondary
                :loading="remoteStarting"
                :disabled="working || remoteStarting"
                @click.stop="startRemoteProcessing"
              >
                <template #icon><n-icon><CloudDownloadOutline /></n-icon></template>
                远程下载并处理
              </n-button>
            </span>
          </template>
          从已配置的 FTP/SFTP 目录递归下载数据，然后自动开始处理。
        </n-tooltip>
      </div>
      <input
        ref="fileInput"
        class="hidden-input"
        type="file"
        multiple
        accept=".zip,.xlsx,.xls,.csv"
        @change="pickFiles"
      />
      <input
        ref="folderInput"
        class="hidden-input"
        type="file"
        multiple
        webkitdirectory
        directory
        @change="pickFiles"
      />
    </section>

    <div v-if="!taskInProgress && files.length > 0" class="file-list">
      <div class="file-list-header">
        <h4>已选择文件</h4>
        <n-button size="small" text :disabled="working" @click="clearFiles">
          <template #icon><n-icon><TrashOutline /></n-icon></template>
          清空
        </n-button>
      </div>

      <div class="file-list-footer">
        <span id="fileCount">{{ files.length }} 个文件</span>
        <n-button type="primary" :disabled="files.length === 0" :loading="working" @click="uploadAndStart">
          <template #icon><n-icon><CloudUploadOutline /></n-icon></template>
          上传并处理
        </n-button>
      </div>

      <div v-if="showUploadProgress" class="total-progress">
        <div class="total-progress-header">
          <span class="label">上传进度</span>
          <span class="percent">{{ uploadProgress }}%</span>
        </div>
        <div class="total-progress-bar">
          <div class="total-progress-bar-inner" :style="{ width: `${uploadProgress}%` }"></div>
        </div>
      </div>

      <div v-if="showUploadProgress" class="upload-stats">
        <div class="upload-stats-item">
          <span>总计:</span>
          <span class="count">{{ files.length }}</span>
        </div>
        <div class="upload-stats-item success">
          <span>已完成:</span>
          <span class="count">{{ uploadedCount }}</span>
        </div>
        <div class="upload-stats-item error">
          <span>失败:</span>
          <span class="count">{{ errorCount }}</span>
        </div>
      </div>

      <div class="file-items">
        <div v-for="item in files" :key="item.path" class="file-item" :class="item.status">
          <span class="file-item-icon">
            <n-icon><DocumentTextOutline /></n-icon>
          </span>
          <span class="file-item-name" :title="item.path">{{ item.path }}</span>
          <span class="file-item-size">{{ formatBytes(item.file.size) }}</span>
          <span class="file-item-status" :class="item.status">
            {{ fileStatusText(item) }}
          </span>
          <div v-if="item.status !== 'pending'" class="file-progress">
            <div class="file-progress-bar" :style="{ width: `${item.progress}%` }"></div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="processVisible" class="process-section">
      <div class="upload-process-card">
        <div class="card-header">
          <div class="card-header-left">
            <span class="card-title">处理进度</span>
            <span class="process-status" :class="statusClass">{{ processStatusText }}</span>
          </div>
          <div class="card-header-right">
            <n-button size="small" secondary @click="checkActiveTask">
              <template #icon><n-icon><RefreshOutline /></n-icon></template>
              刷新
            </n-button>
          </div>
        </div>
        <div class="card-body">
          <n-alert v-if="activeTask?.has_active" type="info" :bordered="false" class="task-alert">
            当前任务：{{ activeTask.task_id }} / {{ activeTask.stage || 'processing' }}
          </n-alert>
          <n-alert v-if="taskStatus?.error" type="error" :bordered="false" class="task-alert">
            {{ taskStatus.error }}
          </n-alert>
          <div class="log-container">
            <pre class="log-content">{{ logText }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useMessage } from 'naive-ui';
import {
  CloudDownloadOutline,
  CloudUploadOutline,
  DocumentTextOutline,
  FolderOpenOutline,
  RefreshOutline,
  TrashOutline
} from '@vicons/ionicons5';

import { apiGet, apiPost, upload } from '../api/client';
import type { ActiveTask, TaskStatus } from '../types';

type FileStatus = 'pending' | 'uploading' | 'uploaded' | 'error';

interface PickedFile {
  file: File;
  path: string;
  status: FileStatus;
  progress: number;
}

interface DroppedFile {
  file: File;
  path: string;
}

interface UploadResponse {
  success: boolean;
  task_id: string;
  file_count?: number;
  message?: string;
  stage?: string;
}

const validExtensions = new Set(['.zip', '.xlsx', '.xls', '.csv']);
const message = useMessage();
const fileInput = ref<HTMLInputElement | null>(null);
const folderInput = ref<HTMLInputElement | null>(null);
const files = ref<PickedFile[]>([]);
const uploadProgress = ref(0);
const working = ref(false);
const remoteStarting = ref(false);
const isDragging = ref(false);
const taskStatus = ref<TaskStatus | null>(null);
const activeTask = ref<ActiveTask | null>(null);
let timer: number | undefined;

const logText = computed(() => taskStatus.value?.logs?.join('\n') || '等待任务开始');
const processVisible = computed(() => Boolean(taskStatus.value || activeTask.value?.has_active));
const taskInProgress = computed(() => {
  if (activeTask.value?.has_active) {
    return true;
  }
  return taskStatus.value ? !['completed', 'failed'].includes(taskStatus.value.status) : false;
});
const showUploadProgress = computed(() => working.value || uploadProgress.value > 0);
const uploadedCount = computed(() => files.value.filter(item => item.status === 'uploaded').length);
const errorCount = computed(() => files.value.filter(item => item.status === 'error').length);
const statusClass = computed(() => {
  if (taskStatus.value?.status === 'completed') return 'completed';
  if (taskStatus.value?.status === 'failed') return 'failed';
  return 'processing';
});
const processStatusText = computed(() => {
  if (taskStatus.value?.status === 'completed') return '处理完成';
  if (taskStatus.value?.status === 'failed') return '处理失败';
  if (activeTask.value?.stage === 'downloading') return '远程下载中...';
  if (activeTask.value?.stage === 'uploading') return '上传中...';
  return '处理中...';
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

function openFilePicker() {
  if (working.value) return;
  fileInput.value?.click();
}

function pickFiles(event: Event) {
  const input = event.target as HTMLInputElement;
  const selected = Array.from(input.files || []).map(toDroppedFile);
  addFiles(selected);
  input.value = '';
}

function onDragEnter() {
  if (!working.value) {
    isDragging.value = true;
  }
}

function onDragOver() {
  if (!working.value) {
    isDragging.value = true;
  }
}

function onDragLeave(event: DragEvent) {
  const target = event.currentTarget as HTMLElement;
  const related = event.relatedTarget as Node | null;
  if (!related || !target.contains(related)) {
    isDragging.value = false;
  }
}

async function onDrop(event: DragEvent) {
  isDragging.value = false;
  if (working.value || !event.dataTransfer) return;

  const dropped = await readDroppedFiles(event.dataTransfer);
  addFiles(dropped);
}

async function readDroppedFiles(dataTransfer: DataTransfer): Promise<DroppedFile[]> {
  const result: DroppedFile[] = [];
  const items = Array.from(dataTransfer.items || []);

  for (const item of items) {
    if (item.kind !== 'file') continue;
    const entry = typeof item.webkitGetAsEntry === 'function' ? item.webkitGetAsEntry() : null;
    if (entry) {
      result.push(...(await traverseEntry(entry, '')));
    }
  }

  if (result.length > 0) {
    return result;
  }

  return Array.from(dataTransfer.files || []).map(toDroppedFile);
}

async function traverseEntry(entry: FileSystemEntry, parentPath: string): Promise<DroppedFile[]> {
  if (entry.isFile) {
    const fileEntry = entry as FileSystemFileEntry;
    const file = await readEntryFile(fileEntry);
    const path = parentPath ? `${parentPath}/${file.name}` : file.name;
    return [{ file, path }];
  }

  if (!entry.isDirectory) {
    return [];
  }

  const directoryEntry = entry as FileSystemDirectoryEntry;
  const nextPath = parentPath ? `${parentPath}/${entry.name}` : entry.name;
  const children = await readAllDirectoryEntries(directoryEntry);
  const nested = await Promise.all(children.map(child => traverseEntry(child, nextPath)));
  return nested.flat();
}

function readEntryFile(entry: FileSystemFileEntry): Promise<File> {
  return new Promise((resolve, reject) => {
    entry.file(resolve, reject);
  });
}

async function readAllDirectoryEntries(entry: FileSystemDirectoryEntry): Promise<FileSystemEntry[]> {
  const reader = entry.createReader();
  const entries: FileSystemEntry[] = [];

  while (true) {
    const batch = await new Promise<FileSystemEntry[]>((resolve, reject) => {
      reader.readEntries(resolve, reject);
    });
    if (batch.length === 0) break;
    entries.push(...batch);
  }

  return entries;
}

function toDroppedFile(file: File): DroppedFile {
  return {
    file,
    path: normalizePath(file.webkitRelativePath || file.name)
  };
}

function addFiles(newFiles: DroppedFile[]) {
  if (working.value || newFiles.length === 0) return;

  let ignored = 0;
  let duplicated = 0;
  const existingPaths = new Set(files.value.map(item => item.path));
  const accepted: PickedFile[] = [];

  for (const item of newFiles) {
    const path = normalizePath(item.path);
    if (!isSupportedFile(path)) {
      ignored += 1;
      continue;
    }
    if (existingPaths.has(path)) {
      duplicated += 1;
      continue;
    }
    existingPaths.add(path);
    accepted.push({
      file: item.file,
      path,
      status: 'pending',
      progress: 0
    });
  }

  if (accepted.length > 0) {
    files.value.push(...accepted);
  }

  if (ignored > 0) {
    message.warning(`已忽略 ${ignored} 个不支持的文件`);
  }
  if (duplicated > 0) {
    message.warning(`已忽略 ${duplicated} 个重复文件`);
  }
  if (accepted.length === 0 && ignored === 0 && duplicated === 0) {
    message.warning('未读取到可上传文件');
  }
}

function isSupportedFile(path: string): boolean {
  const dotIndex = path.lastIndexOf('.');
  if (dotIndex < 0) return false;
  return validExtensions.has(path.slice(dotIndex).toLowerCase());
}

function normalizePath(path: string): string {
  return path.replace(/\\/g, '/');
}

function clearFiles() {
  if (working.value) return;
  files.value = [];
  uploadProgress.value = 0;
}

async function uploadAndStart() {
  if (files.value.length === 0 || working.value) return;

  const formData = new FormData();
  for (const item of files.value) {
    item.status = 'uploading';
    item.progress = 0;
    formData.append('files', item.file, item.path);
  }

  working.value = true;
  uploadProgress.value = 0;
  try {
    const result = await upload<UploadResponse>('/api/upload', formData, value => {
      uploadProgress.value = value;
      updateUploadingFiles(value);
    });
    uploadProgress.value = 100;
    files.value.forEach(item => {
      item.status = 'uploaded';
      item.progress = 100;
    });
    message.success(`上传完成：${result.file_count ?? files.value.length} 个文件`);
    await apiPost('/api/process/start', { task_id: result.task_id });
    taskStatus.value = { task_id: result.task_id, status: 'processing', logs: ['任务已提交，等待处理日志...'] };
    startPolling(result.task_id);
  } catch (error) {
    files.value.forEach(item => {
      if (item.status === 'uploading') {
        item.status = 'error';
      }
    });
    message.error(error instanceof Error ? error.message : '上传或启动任务失败');
  } finally {
    working.value = false;
  }
}

async function startRemoteProcessing() {
  if (working.value || remoteStarting.value) return;

  remoteStarting.value = true;
  try {
    const result = await apiPost<UploadResponse>('/api/remote/start');
    message.success(result.message || '远程自动化任务已启动');
    files.value = [];
    uploadProgress.value = 0;
    activeTask.value = {
      has_active: true,
      task_id: result.task_id,
      stage: result.stage || 'downloading',
      started_at: new Date().toISOString()
    };
    taskStatus.value = { task_id: result.task_id, status: 'processing', logs: ['远程下载任务已提交，等待处理日志...'] };
    startPolling(result.task_id);
  } catch (error) {
    message.error(error instanceof Error ? error.message : '启动远程自动化任务失败');
  } finally {
    remoteStarting.value = false;
  }
}

function updateUploadingFiles(progress: number) {
  files.value.forEach(item => {
    if (item.status === 'uploading') {
      item.progress = progress;
    }
  });
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

function fileStatusText(item: PickedFile): string {
  if (item.status === 'uploading') return `上传中 ${item.progress}%`;
  if (item.status === 'uploaded') return '已完成';
  if (item.status === 'error') return '失败';
  return '等待上传';
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

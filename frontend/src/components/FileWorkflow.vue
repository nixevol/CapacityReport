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
      <span class="upload-card-label">容量数据</span>
      <n-button
        quaternary
        circle
        size="small"
        class="upload-help-button"
        aria-label="查看容量数据说明"
        title="查看说明"
        @click.stop="capacityHelpVisible = true"
      >
        <template #icon>
          <n-icon><InformationCircleOutline /></n-icon>
        </template>
      </n-button>
      <div class="upload-icon">
        <n-icon size="24"><FolderOpenOutline /></n-icon>
      </div>
      <h3>拖拽文件夹或文件到这里</h3>
      <p>支持 .zip, .xlsx, .xls, .csv 格式</p>
      <div class="upload-zone-actions">
        <span class="upload-hint">或者点击选择文件</span>
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
          从已配置的 FTP/SFTP 目录下载数据自动处理。
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

    <section
      v-if="!taskInProgress"
      class="cell-data-upload-zone"
      :class="{ dragover: isCellDataDragging, disabled: cellDataStarting }"
      role="button"
      tabindex="0"
      :aria-disabled="cellDataStarting"
      @click="cellDataFolderInput?.click()"
      @keydown.enter.prevent="cellDataFolderInput?.click()"
      @keydown.space.prevent="cellDataFolderInput?.click()"
      @dragenter.prevent.stop="onCellDataDragEnter"
      @dragover.prevent.stop="onCellDataDragOver"
      @dragleave="onCellDataDragLeave"
      @drop.prevent.stop="onCellDataDrop"
    >
      <span class="upload-card-label">CellData</span>
      <n-button
        quaternary
        circle
        size="small"
        class="upload-help-button"
        aria-label="查看 CellData 文件说明"
        title="查看说明"
        @click.stop="cellDataHelpVisible = true"
      >
        <template #icon>
          <n-icon><InformationCircleOutline /></n-icon>
        </template>
      </n-button>
      <div class="upload-icon">
        <n-icon size="24"><FolderOpenOutline /></n-icon>
      </div>
      <div class="cell-data-upload-text">
        <h3>拖拽文件夹到这里</h3>
        <p>包含 700M、2.6G 等目录</p>
      </div>
      <div class="upload-zone-actions">
        <span class="upload-hint">或者点击选择文件夹</span>
        <n-space size="small" @click.stop @keydown.stop>
          <n-button
            type="primary"
            secondary
            :loading="cellDataStarting"
            :disabled="working || remoteStarting || cellDataStarting"
            @click="startCellDataProcessing"
          >
            <template #icon><n-icon><CloudDownloadOutline /></n-icon></template>
            远程刷新
          </n-button>
        </n-space>
      </div>
      <input
        ref="cellDataFolderInput"
        class="hidden-input"
        type="file"
        multiple
        webkitdirectory
        directory
        @change="pickCellDataFiles"
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

    <div v-if="processVisible" class="process-section" :class="{ finished: taskFinished }">
      <div class="upload-process-card">
        <div class="card-header">
          <div class="card-header-left">
            <span class="card-title">处理进度</span>
            <span class="process-status" :class="statusClass">{{ processStatusText }}</span>
          </div>
          <div class="card-header-right">
            <n-checkbox v-model:checked="keepLatestLog" size="small">保持最新 Log</n-checkbox>
            <n-button size="small" secondary @click="checkActiveTask">
              <template #icon><n-icon><RefreshOutline /></n-icon></template>
              刷新
            </n-button>
          </div>
        </div>
        <div class="card-body">
          <n-alert v-if="activeTask?.has_active" type="info" :bordered="false" class="task-alert">
            当前任务：{{ activeTask.task_id }} / {{ currentStageText }}
          </n-alert>
          <n-alert v-if="taskStatus?.error" type="error" :bordered="false" class="task-alert">
            {{ taskStatus.error }}
          </n-alert>
          <div ref="logContainer" class="log-container">
            <pre class="colored-log-content"><span
              v-for="(line, index) in logLines"
              :key="index"
              class="colored-log-line"
              :class="`log-level-${line.level}`"
            >{{ line.text }}</span></pre>
          </div>
        </div>
      </div>
    </div>

    <n-modal
      v-model:show="licenseModalVisible"
      preset="card"
      title="授权已过期"
      :mask-closable="!activationLoading"
      :style="{ width: '420px', maxWidth: 'calc(100vw - 32px)' }"
    >
      <div class="license-dialog-body">
        <p class="license-dialog-text">{{ licenseErrorMessage }}</p>
        <div class="license-key-label">key: {{ activationKeyLabel }}</div>
        <n-input
          v-model:value="activationCode"
          type="textarea"
          :autosize="{ minRows: 3, maxRows: 5 }"
          placeholder="请输入激活码"
          :disabled="activationLoading"
        />
      </div>
      <template #footer>
        <div class="license-dialog-footer">
          <n-button :disabled="activationLoading" @click="licenseModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="activationLoading" @click="submitActivation">激活</n-button>
        </div>
      </template>
    </n-modal>

    <n-modal
      v-model:show="capacityHelpVisible"
      preset="card"
      class="cell-data-help-modal"
      title="容量数据说明"
      :style="{ width: 'min(520px, calc(100vw - 32px))' }"
    >
      <n-scrollbar class="cell-data-help-scroll">
        <section class="cell-data-help-section">
          <h4>支持格式</h4>
          <p>支持 ZIP、Excel 和 CSV 文件。</p>
        </section>
        <section class="cell-data-help-section">
          <h4>上传方式</h4>
          <p>可拖拽文件或文件夹，也可点击卡片选择文件。</p>
        </section>
        <section class="cell-data-help-section">
          <h4>远程处理</h4>
          <p>使用系统设置中的数据源配置下载并处理。</p>
        </section>
      </n-scrollbar>
    </n-modal>

    <n-modal
      v-model:show="cellDataHelpVisible"
      preset="card"
      class="cell-data-help-modal"
      title="CellData 文件说明"
      :style="{ width: 'min(520px, calc(100vw - 32px))' }"
    >
      <n-scrollbar class="cell-data-help-scroll">
        <section class="cell-data-help-section">
          <h4>目录结构</h4>
          <p>请选择包含频段目录的文件夹，例如：</p>
          <code>300表/700M/Result_300_*.zip</code>
          <code>300表/2.6G/Result_300_*.zip</code>
        </section>
        <section class="cell-data-help-section">
          <h4>文件要求</h4>
          <p>只处理文件名以 <strong>Result_300_</strong> 开头的 ZIP。</p>
          <p>每个频段目录只取文件名末尾时间戳最新的 ZIP。</p>
        </section>
        <section class="cell-data-help-section">
          <h4>ZIP 内容</h4>
          <p>识别以下 CSV 文件名前缀：</p>
          <code>LTE_ITBBU_CellInfo</code>
          <code>LTE_SDR_CellInfo</code>
          <code>NR_CellInfo</code>
        </section>
      </n-scrollbar>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useMessage } from 'naive-ui';
import {
  CloudDownloadOutline,
  CloudUploadOutline,
  DocumentTextOutline,
  FolderOpenOutline,
  InformationCircleOutline,
  RefreshOutline,
  TrashOutline
} from '@vicons/ionicons5';

import { ApiRequestError, apiGet, apiPost, upload } from '../api/client';
import type { ActiveTask, ApiErrorDetail, LicenseStatus, TaskStatus } from '../types';
import { toColoredLogLines } from '../composables/logLines';

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
const cellDataFolderInput = ref<HTMLInputElement | null>(null);
const files = ref<PickedFile[]>([]);
const uploadProgress = ref(0);
const working = ref(false);
const remoteStarting = ref(false);
const cellDataStarting = ref(false);
const isDragging = ref(false);
const isCellDataDragging = ref(false);
const capacityHelpVisible = ref(false);
const cellDataHelpVisible = ref(false);
const taskStatus = ref<TaskStatus | null>(null);
const activeTask = ref<ActiveTask | null>(null);
const keepLatestLog = ref(false);
const logContainer = ref<HTMLElement | null>(null);
const licenseModalVisible = ref(false);
const activationCode = ref('');
const activationLoading = ref(false);
const activationKeyLabel = ref('2026/12/30');
const licenseErrorMessage = ref('当前数据日期已超过授权到期日期，请输入激活码延长 30 天。');
const taskMode = ref<'local' | 'remote' | 'cell_data' | 'unknown'>('unknown');
let activationRetry: (() => Promise<void>) | null = null;
let timer: number | undefined;

const stageLabels: Record<string, string> = {
  license: '授权校验中...',
  locating: '定位数据中...',
  downloading: '远程下载中...',
  uploading: '上传文件中...',
  processing: '处理中...',
  extracting: '解压数据中...',
  converting: '转换 Excel 中...',
  parsing: '解析数据中...',
  importing: '上传数据中...',
  scripting: '运行脚本中...',
  completed: '处理完成',
  failed: '处理失败'
};

const logText = computed(() => taskStatus.value?.logs?.join('\n') || '等待任务开始');
const logLines = computed(() => toColoredLogLines(logText.value, '等待任务开始'));
const processVisible = computed(() => Boolean(taskStatus.value || activeTask.value?.has_active));
const taskInProgress = computed(() => {
  if (activeTask.value?.has_active) {
    return true;
  }
  return taskStatus.value ? !['completed', 'failed'].includes(taskStatus.value.status) : false;
});
const taskFinished = computed(() => {
  return taskStatus.value ? ['completed', 'failed'].includes(taskStatus.value.status) : false;
});
const showUploadProgress = computed(() => working.value || uploadProgress.value > 0);
const uploadedCount = computed(() => files.value.filter(item => item.status === 'uploaded').length);
const errorCount = computed(() => files.value.filter(item => item.status === 'error').length);
const statusClass = computed(() => {
  if (taskStatus.value?.status === 'completed') return 'completed';
  if (taskStatus.value?.status === 'failed') return 'failed';
  return 'processing';
});
const currentStage = computed(() => taskStatus.value?.stage || activeTask.value?.stage || 'processing');
const currentStageText = computed(() => stageText(currentStage.value));
const processStatusText = computed(() => {
  if (taskStatus.value?.status === 'completed') return '处理完成';
  if (taskStatus.value?.status === 'failed') return '处理失败';
  return currentStageText.value;
});

watch(
  () => taskStatus.value?.logs?.length ?? 0,
  () => {
    if (keepLatestLog.value) {
      void nextTick(scrollLogToBottom);
    }
  }
);

watch(keepLatestLog, checked => {
  if (checked) {
    void nextTick(scrollLogToBottom);
  }
});

onMounted(() => {
  const folder = folderInput.value as (HTMLInputElement & { webkitdirectory?: boolean }) | null;
  if (folder) {
    folder.webkitdirectory = true;
  }
  const cellDataFolder = cellDataFolderInput.value as (HTMLInputElement & { webkitdirectory?: boolean }) | null;
  if (cellDataFolder) {
    cellDataFolder.webkitdirectory = true;
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

function onCellDataDragEnter() {
  if (!cellDataStarting.value && !taskInProgress.value) {
    isCellDataDragging.value = true;
  }
}

function onCellDataDragOver() {
  if (!cellDataStarting.value && !taskInProgress.value) {
    isCellDataDragging.value = true;
  }
}

function onCellDataDragLeave(event: DragEvent) {
  const target = event.currentTarget as HTMLElement;
  const related = event.relatedTarget as Node | null;
  if (!related || !target.contains(related)) {
    isCellDataDragging.value = false;
  }
}

async function onCellDataDrop(event: DragEvent) {
  isCellDataDragging.value = false;
  if (cellDataStarting.value || taskInProgress.value || !event.dataTransfer) return;
  if (!hasDroppedDirectory(event.dataTransfer)) {
    message.warning('请拖入包含 Result_300 ZIP 的文件夹');
    return;
  }
  await startCellDataUpload(await readDroppedFiles(event.dataTransfer));
}

async function pickCellDataFiles(event: Event) {
  const input = event.target as HTMLInputElement;
  const selected = Array.from(input.files || []).map(toDroppedFile);
  input.value = '';
  await startCellDataUpload(selected);
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

function hasDroppedDirectory(dataTransfer: DataTransfer): boolean {
  return Array.from(dataTransfer.items || []).some(item => {
    if (item.kind !== 'file' || typeof item.webkitGetAsEntry !== 'function') return false;
    return Boolean(item.webkitGetAsEntry()?.isDirectory);
  });
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

function isCellDataZip(path: string): boolean {
  const name = normalizePath(path).split('/').pop() || '';
  return /^Result_300_.*\.zip$/i.test(name);
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
    await startUploadedTask(result.task_id);
  } catch (error) {
    files.value.forEach(item => {
      if (item.status === 'uploading') {
        item.status = 'error';
      }
    });
    if (!handleApiLicenseError(error)) {
      message.error(error instanceof Error ? error.message : '上传或启动任务失败');
    }
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
    taskStatus.value = {
      task_id: result.task_id,
      status: 'processing',
      stage: result.stage || 'downloading',
      logs: ['远程下载任务已提交，等待处理日志...']
    };
    taskMode.value = 'remote';
    startPolling(result.task_id);
  } catch (error) {
    if (!handleApiLicenseError(error)) {
      message.error(error instanceof Error ? error.message : '启动远程自动化任务失败');
    }
  } finally {
    remoteStarting.value = false;
  }
}

async function startCellDataProcessing() {
  if (working.value || remoteStarting.value || cellDataStarting.value) return;

  cellDataStarting.value = true;
  try {
    const result = await apiPost<UploadResponse>('/api/cell-data/process/start');
    message.success(result.message || 'CellData 处理已启动');
    activeTask.value = {
      has_active: true,
      task_id: result.task_id,
      stage: result.stage || 'locating',
      started_at: new Date().toISOString()
    };
    taskStatus.value = {
      task_id: result.task_id,
      status: 'processing',
      stage: result.stage || 'locating',
      logs: ['CellData 任务已提交，等待处理日志...']
    };
    taskMode.value = 'cell_data';
    startPolling(result.task_id);
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'CellData 处理启动失败');
  } finally {
    cellDataStarting.value = false;
  }
}

async function startCellDataUpload(items: DroppedFile[]) {
  if (cellDataStarting.value || taskInProgress.value) return;
  const accepted = items
    .map(item => ({ ...item, path: normalizePath(item.path) }))
    .filter(item => isCellDataZip(item.path));
  if (accepted.length === 0) {
    message.warning('请选择 Result_300 ZIP 文件');
    return;
  }

  const formData = new FormData();
  for (const item of accepted) {
    formData.append('files', item.file, item.path);
  }

  cellDataStarting.value = true;
  try {
    const result = await upload<UploadResponse>('/api/cell-data/process/upload', formData);
    message.success(result.message || `已上传 ${accepted.length} 个文件`);
    activeTask.value = {
      has_active: true,
      task_id: result.task_id,
      stage: result.stage || 'parsing',
      started_at: new Date().toISOString()
    };
    taskStatus.value = {
      task_id: result.task_id,
      status: 'processing',
      stage: result.stage || 'parsing',
      logs: ['CellData 文件已上传，等待处理日志...']
    };
    taskMode.value = 'cell_data';
    startPolling(result.task_id);
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'CellData 上传处理失败');
  } finally {
    cellDataStarting.value = false;
  }
}

async function startUploadedTask(taskId: string) {
  await apiPost('/api/process/start', { task_id: taskId });
  taskMode.value = 'local';
  taskStatus.value = {
    task_id: taskId,
    status: 'processing',
    stage: 'license',
    logs: ['任务已提交，等待处理日志...']
  };
  startPolling(taskId);
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
      taskMode.value = activeTask.value.task_id.startsWith('cell_data_') ? 'cell_data' : 'unknown';
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
    const statusUrl = taskMode.value === 'cell_data'
      ? '/api/cell-data/process/status'
      : '/api/process/status';
    taskStatus.value = await apiPost<TaskStatus>(statusUrl, { task_id: taskId });
    if (activeTask.value?.has_active && taskStatus.value.stage) {
      activeTask.value = { ...activeTask.value, stage: taskStatus.value.stage };
    }
    if (['completed', 'failed'].includes(taskStatus.value.status)) {
      stopPolling();
      await checkActiveTask();
      if (taskStatus.value.status === 'failed') {
        handleTaskLicenseError(taskStatus.value);
      }
    }
  } catch (error) {
    stopPolling();
    message.error(error instanceof Error ? error.message : '刷新任务状态失败');
  }
}

function handleTaskLicenseError(status: TaskStatus): boolean {
  const detail = status.error_detail || parseLicenseDetail(status.error || '');
  if (detail?.code !== 'LICENSE_EXPIRED') {
    return false;
  }

  const taskId = status.task_id;
  const retry =
    taskMode.value === 'local'
      ? () => startUploadedTask(taskId)
      : taskMode.value === 'remote'
        ? () => startRemoteProcessing()
        : null;
  openLicenseModal(detail, retry);
  return true;
}

function handleApiLicenseError(error: unknown): boolean {
  if (!(error instanceof ApiRequestError) || error.code !== 'LICENSE_EXPIRED') {
    return false;
  }

  openLicenseModal(error.detail);
  return true;
}

function openLicenseModal(detail?: ApiErrorDetail, retry?: (() => Promise<void>) | null) {
  activationKeyLabel.value = detail?.key_label || activationKeyLabel.value;
  licenseErrorMessage.value =
    detail?.message || '当前数据日期已超过授权到期日期，请输入激活码延长 30 天。';
  activationCode.value = '';
  activationRetry = retry || null;
  licenseModalVisible.value = true;
}

async function submitActivation() {
  const code = activationCode.value.trim();
  if (!code) {
    message.warning('请输入激活码');
    return;
  }

  activationLoading.value = true;
  try {
    const result = await apiPost<LicenseStatus>('/api/license/activate', { code });
    activationKeyLabel.value = result.key_label;
    licenseModalVisible.value = false;
    message.success(`激活成功，到期日期: ${result.expires_on}`);
    if (activationRetry) {
      const retry = activationRetry;
      activationRetry = null;
      await retry();
    }
  } catch (error) {
    if (error instanceof ApiRequestError && error.detail?.key_label) {
      activationKeyLabel.value = error.detail.key_label;
    }
    message.error(error instanceof Error ? error.message : '激活失败');
  } finally {
    activationLoading.value = false;
  }
}

function parseLicenseDetail(text: string): ApiErrorDetail | null {
  if (!text.includes('授权已过期')) {
    return null;
  }

  const expiresMatch = text.match(/到期日期\s+(\d{4}-\d{2}-\d{2})/);
  const currentMatch = text.match(/数据日期\s+(\d{4}-\d{2}-\d{2})/);
  const expiresOn = expiresMatch?.[1];
  return {
    code: 'LICENSE_EXPIRED',
    message: text,
    expires_on: expiresOn,
    current_date: currentMatch?.[1],
    key_label: expiresOn ? expiresOn.replace(/-/g, '/') : activationKeyLabel.value
  };
}

function stageText(stage?: string | null): string {
  if (!stage) return '处理中...';
  return stageLabels[stage] || '处理中...';
}

function scrollLogToBottom() {
  const container = logContainer.value;
  if (container) {
    container.scrollTop = container.scrollHeight;
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

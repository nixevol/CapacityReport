<template>
  <div class="history-page-body">
    <n-spin v-if="loading" class="page-loading" />

    <div v-else-if="records.length === 0" class="empty-state history-empty-state">
      <n-icon class="empty-icon"><FileTrayOutline /></n-icon>
      <p>暂无处理记录</p>
    </div>

    <div v-else class="history-list">
      <div v-for="record in records" :key="record.id" class="history-item">
        <div class="history-status" :class="record.status"></div>
        <div class="history-info">
          <div class="history-id">{{ record.id }}</div>
          <div class="history-meta">
            {{ formatDate(record.timestamp) }} · {{ record.file_count }} 个文件 · {{ formatElapsed(record.elapsed_time) }}
          </div>
        </div>
        <span class="record-size">{{ statusText(record.status) }}</span>
        <div class="history-actions">
          <n-button
            size="small"
            tertiary
            :loading="downloadingRecordId === record.id"
            :disabled="record.status === 'pending' || record.status === 'processing'"
            @click="downloadHistory(record)"
          >
            <template #icon><n-icon><DownloadOutline /></n-icon></template>
            下载
          </n-button>
          <n-button size="small" tertiary @click="openDetail(record.id)">详情</n-button>
          <n-button size="small" tertiary type="error" @click="confirmDelete(record.id)">删除</n-button>
        </div>
      </div>
    </div>

    <n-modal v-model:show="detailVisible" preset="card" class="history-detail-modal" title="任务详情">
      <n-empty v-if="!detail" description="暂无详情" />
      <n-space v-else vertical size="large">
        <n-tabs v-model:value="detailTab" type="segment" animated>
          <n-tab-pane name="detail" tab="详情">
            <div class="detail-info-list">
              <div class="detail-info-row">
                <span class="detail-info-label">任务 ID</span>
                <span class="detail-info-value monospace">{{ detail.id }}</span>
              </div>
              <div class="detail-info-row">
                <span class="detail-info-label">状态</span>
                <span class="detail-info-value">{{ statusText(detail.status) }}</span>
              </div>
              <div class="detail-info-row">
                <span class="detail-info-label">文件数</span>
                <span class="detail-info-value">{{ detail.file_count }}</span>
              </div>
              <div class="detail-info-row">
                <span class="detail-info-label">耗时</span>
                <span class="detail-info-value">{{ formatElapsed(detail.elapsed_time) }}</span>
              </div>
              <div class="detail-info-row">
                <span class="detail-info-label">创建时间</span>
                <span class="detail-info-value monospace">{{ formatDate(detail.timestamp) }}</span>
              </div>
              <div class="detail-info-row">
                <span class="detail-info-label">占用</span>
                <span class="detail-info-value" :class="{ muted: recordSizeLoading }">{{ recordSize }}</span>
              </div>
              <div class="detail-info-row">
                <span class="detail-info-label">工作目录</span>
                <span class="detail-info-value path-value">{{ detail.work_dir }}</span>
              </div>
              <div v-if="detail.error" class="detail-info-row error-row">
                <span class="detail-info-label">错误</span>
                <span class="detail-info-value">{{ detail.error }}</span>
              </div>
            </div>
          </n-tab-pane>
          <n-tab-pane name="files" tab="文件">
            <div class="history-file-browser">
              <div class="history-file-toolbar">
                <div class="history-file-breadcrumb">
                  <button type="button" class="breadcrumb-link" @click="loadHistoryFiles('')">根目录</button>
                  <template v-for="crumb in fileBreadcrumbs" :key="crumb.path">
                    <n-icon class="breadcrumb-separator"><ChevronForwardOutline /></n-icon>
                    <button type="button" class="breadcrumb-link" @click="loadHistoryFiles(crumb.path)">
                      {{ crumb.name }}
                    </button>
                  </template>
                </div>
                <div class="history-file-toolbar-actions">
                  <n-button size="small" tertiary :disabled="fileParentPath === null || fileLoading" @click="loadHistoryFiles(fileParentPath || '')">
                    <template #icon><n-icon><ArrowBackOutline /></n-icon></template>
                    上一级
                  </n-button>
                  <n-button size="small" tertiary :loading="fileLoading" @click="reloadHistoryFiles">
                    <template #icon><n-icon><RefreshOutline /></n-icon></template>
                    刷新
                  </n-button>
                </div>
              </div>

              <n-spin :show="fileLoading">
                <n-empty v-if="!fileEntries.length && !fileLoading" description="当前目录为空" />
                <div v-else class="history-file-list">
                  <div v-for="entry in fileEntries" :key="entry.path" class="history-file-row">
                    <div class="history-file-main">
                      <n-icon class="history-file-icon" :class="entry.type">
                        <FolderOpenOutline v-if="entry.type === 'dir'" />
                        <DocumentOutline v-else />
                      </n-icon>
                      <div class="history-file-text">
                        <button
                          type="button"
                          class="history-file-name"
                          :disabled="entry.type !== 'dir'"
                          @click="entry.type === 'dir' && loadHistoryFiles(entry.path)"
                        >
                          {{ entry.name }}
                        </button>
                        <span class="history-file-meta">
                          {{ entry.type === 'dir' ? '目录' : '文件' }} · {{ entry.size_formatted }} · {{ entry.modified_formatted }}
                        </span>
                      </div>
                    </div>
                    <div class="history-file-actions">
                      <n-button
                        v-if="entry.type === 'dir'"
                        size="small"
                        tertiary
                        @click="loadHistoryFiles(entry.path)"
                      >
                        打开
                      </n-button>
                      <n-button
                        size="small"
                        tertiary
                        :loading="downloadingFilePath === entry.path"
                        :disabled="detailDownloadDisabled"
                        @click="downloadHistoryItem(entry)"
                      >
                        <template #icon><n-icon><DownloadOutline /></n-icon></template>
                        下载
                      </n-button>
                    </div>
                  </div>
                </div>
              </n-spin>
            </div>
          </n-tab-pane>
        </n-tabs>

        <div>
          <div class="section-label log-section-header">
            <span>处理日志</span>
            <n-button size="small" tertiary circle title="复制日志" :disabled="!detailLogText" @click="copyDetailLogs">
              <template #icon><n-icon><CopyOutline /></n-icon></template>
            </n-button>
          </div>
          <div class="colored-log-panel" role="log" aria-label="处理日志">
            <pre class="colored-log-content"><span
              v-for="(line, index) in detailLogLines"
              :key="index"
              class="colored-log-line"
              :class="`log-level-${line.level}`"
            >{{ line.text }}</span></pre>
          </div>
        </div>
      </n-space>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useDialog, useMessage } from 'naive-ui';
import {
  ArrowBackOutline,
  ChevronForwardOutline,
  CopyOutline,
  DocumentOutline,
  DownloadOutline,
  FileTrayOutline,
  FolderOpenOutline,
  RefreshOutline,
  TrashOutline
} from '@vicons/ionicons5';

import { apiGet, apiPost, download as downloadFile } from '../api/client';
import type { CacheSize, HistoryDetail, HistoryFileEntry, HistoryFilesResponse, HistoryRecord } from '../types';
import { showDownloadCompleteDialog } from '../composables/downloadFeedback';
import { toColoredLogLines } from '../composables/logLines';
import { resetPageHeader, setPageHeader } from '../composables/pageHeader';

const message = useMessage();
const dialog = useDialog();
const records = ref<HistoryRecord[]>([]);
const detail = ref<HistoryDetail | null>(null);
const detailVisible = ref(false);
const cacheSize = ref<CacheSize | null>(null);
const recordSize = ref('-');
const recordSizeLoading = ref(false);
const loading = ref(false);
const downloadingRecordId = ref<string | null>(null);
const detailTab = ref<'detail' | 'files'>('detail');
const fileEntries = ref<HistoryFileEntry[]>([]);
const fileCurrentPath = ref('');
const fileParentPath = ref<string | null>(null);
const fileLoading = ref(false);
const downloadingFilePath = ref<string | null>(null);
let recordSizeToken = 0;
let fileListToken = 0;

const totalSizeText = computed(() => `总占用: ${cacheSize.value?.size_formatted || '计算中...'}`);
const hasRecords = computed(() => records.value.length > 0);
const detailLogText = computed(() => detail.value?.logs?.join('\n') || '');
const detailLogLines = computed(() => toColoredLogLines(detailLogText.value));
const detailDownloadDisabled = computed(() => {
  const status = detail.value?.status;
  return status === 'pending' || status === 'processing';
});
const fileBreadcrumbs = computed(() => {
  let currentPath = '';
  return fileCurrentPath.value
    .split('/')
    .filter(Boolean)
    .map(name => {
      currentPath = currentPath ? `${currentPath}/${name}` : name;
      return { name, path: currentPath };
    });
});

onMounted(() => {
  setPageHeader({
    actions: [
      { key: 'refresh-history', label: '刷新', icon: RefreshOutline, loading, onClick: loadHistory },
      {
        key: 'clear-history',
        label: '清空历史',
        icon: TrashOutline,
        type: 'error',
        variant: 'solid',
        disabled: computed(() => !hasRecords.value),
        onClick: confirmClear
      },
      { key: 'history-size', kind: 'text', label: totalSizeText }
    ]
  });
  void loadHistory();
});

onBeforeUnmount(() => {
  resetPageHeader();
});

watch(detailTab, tab => {
  if (tab === 'files' && detail.value && fileEntries.value.length === 0 && !fileLoading.value) {
    void loadHistoryFiles(fileCurrentPath.value);
  }
});

async function loadHistory() {
  loading.value = true;
  try {
    const [historyResult, sizeResult] = await Promise.all([
      apiPost<{ records: HistoryRecord[] }>('/api/history', { limit: 50 }),
      apiGet<CacheSize>('/api/cache/size')
    ]);
    records.value = historyResult.records;
    cacheSize.value = sizeResult;
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载历史记录失败');
  } finally {
    loading.value = false;
  }
}

async function openDetail(recordId: string) {
  try {
    detail.value = await apiPost<HistoryDetail>('/api/history/detail', { record_id: recordId });
    detailTab.value = 'detail';
    resetFileBrowser();
    detailVisible.value = true;
    void loadRecordSize(recordId);
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载任务详情失败');
  }
}

function resetFileBrowser() {
  fileEntries.value = [];
  fileCurrentPath.value = '';
  fileParentPath.value = null;
  downloadingFilePath.value = null;
  fileListToken += 1;
}

async function downloadHistory(record: HistoryRecord) {
  if (record.status === 'pending' || record.status === 'processing') {
    message.warning('任务尚未完成，暂不能下载历史数据');
    return;
  }

  downloadingRecordId.value = record.id;
  try {
    const filename = `${record.id}.zip`;
    const result = await downloadFile('/api/history/download', { record_id: record.id }, filename);
    if (result.saved) {
      showDownloadCompleteDialog(dialog, filename, result.path);
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '下载历史数据失败');
  } finally {
    downloadingRecordId.value = null;
  }
}

async function loadHistoryFiles(path: string) {
  if (!detail.value) return;

  const currentToken = ++fileListToken;
  fileLoading.value = true;
  try {
    const result = await apiPost<HistoryFilesResponse>('/api/history/files', {
      record_id: detail.value.id,
      path
    });
    if (currentToken !== fileListToken) return;
    fileEntries.value = result.entries;
    fileCurrentPath.value = result.path;
    fileParentPath.value = result.parent_path;
  } catch (error) {
    if (currentToken !== fileListToken) return;
    message.error(error instanceof Error ? error.message : '加载历史文件失败');
  } finally {
    if (currentToken === fileListToken) {
      fileLoading.value = false;
    }
  }
}

function reloadHistoryFiles() {
  void loadHistoryFiles(fileCurrentPath.value);
}

async function downloadHistoryItem(entry: HistoryFileEntry) {
  if (!detail.value) return;
  if (detailDownloadDisabled.value) {
    message.warning('任务尚未完成，暂不能下载历史数据');
    return;
  }

  downloadingFilePath.value = entry.path;
  try {
    const fallbackFilename = entry.type === 'dir' ? `${entry.name}.zip` : entry.name;
    const result = await downloadFile(
      '/api/history/file/download',
      { record_id: detail.value.id, path: entry.path },
      fallbackFilename
    );
    if (result.saved) {
      showDownloadCompleteDialog(dialog, fallbackFilename, result.path);
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '下载历史文件失败');
  } finally {
    downloadingFilePath.value = null;
  }
}

async function loadRecordSize(recordId: string) {
  const currentToken = ++recordSizeToken;
  recordSize.value = '计算中...';
  recordSizeLoading.value = true;
  try {
    const result = await apiPost<{ success: boolean; size_formatted: string }>('/api/history/size', {
      record_id: recordId
    });
    if (currentToken !== recordSizeToken) return;
    recordSize.value = result.size_formatted;
  } catch (error) {
    if (currentToken !== recordSizeToken) return;
    recordSize.value = '计算失败';
    message.error(error instanceof Error ? error.message : '计算目录占用失败');
  } finally {
    if (currentToken === recordSizeToken) {
      recordSizeLoading.value = false;
    }
  }
}

async function copyDetailLogs() {
  if (!detailLogText.value) {
    message.warning('暂无可复制日志');
    return;
  }

  try {
    await writeClipboardText(detailLogText.value);
    message.success('日志已复制');
  } catch {
    message.error('复制日志失败');
  }
}

async function writeClipboardText(text: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', 'true');
  textarea.style.position = 'fixed';
  textarea.style.top = '-1000px';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();

  try {
    if (!document.execCommand('copy')) {
      throw new Error('copy failed');
    }
  } finally {
    document.body.removeChild(textarea);
  }
}

function confirmDelete(recordId: string) {
  dialog.warning({
    title: '删除历史记录',
    content: `确认删除任务 ${recordId} 及其缓存文件？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: () => deleteRecord(recordId)
  });
}

async function deleteRecord(recordId: string) {
  try {
    await apiPost('/api/history/delete', { record_id: recordId });
    if (detail.value?.id === recordId) {
      detail.value = null;
      detailVisible.value = false;
    }
    message.success('删除成功');
    await loadHistory();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '删除失败');
  }
}

function confirmClear() {
  dialog.warning({
    title: '清空历史记录',
    content: '确认清空全部历史记录和缓存文件？',
    positiveText: '清空',
    negativeText: '取消',
    onPositiveClick: clearHistory
  });
}

async function clearHistory() {
  try {
    await apiPost('/api/history/clear');
    detail.value = null;
    detailVisible.value = false;
    message.success('已清空历史记录');
    await loadHistory();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '清空失败');
  }
}

function statusText(status: string): string {
  const map: Record<string, string> = {
    pending: '待处理',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  };
  return map[status] || status;
}

function formatDate(value: string): string {
  if (!value) return '-';
  return value.replace('T', ' ').slice(0, 19);
}

function formatElapsed(value: number): string {
  if (!value) return '-';
  return `${value.toFixed(1)} 秒`;
}
</script>

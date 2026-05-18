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
          <n-button size="small" tertiary @click="openDetail(record.id)">详情</n-button>
          <n-button size="small" tertiary type="error" @click="confirmDelete(record.id)">删除</n-button>
        </div>
      </div>
    </div>

    <n-modal v-model:show="detailVisible" preset="card" class="history-detail-modal" title="任务详情">
      <n-empty v-if="!detail" description="暂无详情" />
      <n-space v-else vertical size="large">
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

        <div>
          <div class="section-label">处理日志</div>
          <n-log :log="detail.logs.join('\n') || '暂无日志'" language="text" trim class="log-panel" />
        </div>
      </n-space>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useDialog, useMessage } from 'naive-ui';
import { FileTrayOutline, RefreshOutline, TrashOutline } from '@vicons/ionicons5';

import { apiGet, apiPost } from '../api/client';
import type { CacheSize, HistoryDetail, HistoryRecord } from '../types';
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
let recordSizeToken = 0;

const totalSizeText = computed(() => `总占用: ${cacheSize.value?.size_formatted || '计算中...'}`);
const hasRecords = computed(() => records.value.length > 0);

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
    detailVisible.value = true;
    void loadRecordSize(recordId);
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载任务详情失败');
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

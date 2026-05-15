<template>
  <n-grid :cols="12" :x-gap="16" :y-gap="16" responsive="screen">
    <n-gi :span="12" :m="5">
      <n-card title="处理历史" size="small">
        <template #header-extra>
          <n-space>
            <n-button size="small" tertiary :loading="loading" @click="loadHistory">刷新</n-button>
            <n-button size="small" type="error" tertiary :disabled="records.length === 0" @click="confirmClear">
              清空
            </n-button>
          </n-space>
        </template>

        <n-space vertical>
          <n-alert v-if="cacheSize" type="default" :bordered="false">
            缓存占用：{{ cacheSize.size_formatted }}，目录 {{ cacheSize.dir_count }} 个
          </n-alert>

          <n-empty v-if="records.length === 0 && !loading" description="暂无历史记录" />
          <n-scrollbar v-else class="history-list">
            <n-list bordered>
              <n-list-item v-for="record in records" :key="record.id">
                <n-thing :title="record.id" :description="recordSummary(record)">
                  <template #header-extra>
                    <n-tag size="small" :type="statusType(record.status)">{{ statusText(record.status) }}</n-tag>
                  </template>
                  <template #action>
                    <n-space>
                      <n-button size="small" @click="openDetail(record.id)">详情</n-button>
                      <n-button size="small" tertiary type="error" @click="confirmDelete(record.id)">删除</n-button>
                    </n-space>
                  </template>
                </n-thing>
              </n-list-item>
            </n-list>
          </n-scrollbar>
        </n-space>
      </n-card>
    </n-gi>

    <n-gi :span="12" :m="7">
      <n-card title="任务详情" size="small">
        <template #header-extra>
          <n-button v-if="detail" size="small" tertiary @click="loadRecordSize(detail.id)">计算占用</n-button>
        </template>

        <n-empty v-if="!detail" description="请选择一条历史记录" />
        <n-space v-else vertical size="large">
          <n-descriptions bordered size="small" :column="2">
            <n-descriptions-item label="任务 ID">{{ detail.id }}</n-descriptions-item>
            <n-descriptions-item label="状态">{{ statusText(detail.status) }}</n-descriptions-item>
            <n-descriptions-item label="文件数">{{ detail.file_count }}</n-descriptions-item>
            <n-descriptions-item label="耗时">{{ formatElapsed(detail.elapsed_time) }}</n-descriptions-item>
            <n-descriptions-item label="创建时间">{{ formatDate(detail.timestamp) }}</n-descriptions-item>
            <n-descriptions-item label="占用">{{ recordSize }}</n-descriptions-item>
            <n-descriptions-item label="工作目录" :span="2">{{ detail.work_dir }}</n-descriptions-item>
            <n-descriptions-item v-if="detail.error" label="错误" :span="2">{{ detail.error }}</n-descriptions-item>
          </n-descriptions>

          <div>
            <div class="section-label">处理日志</div>
            <n-log :log="detail.logs.join('\n') || '暂无日志'" language="text" trim class="log-panel" />
          </div>
        </n-space>
      </n-card>
    </n-gi>
  </n-grid>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useDialog, useMessage } from 'naive-ui';
import type { TagProps } from 'naive-ui';

import { apiGet, apiPost } from '../api/client';
import type { CacheSize, HistoryDetail, HistoryRecord } from '../types';

const message = useMessage();
const dialog = useDialog();
const records = ref<HistoryRecord[]>([]);
const detail = ref<HistoryDetail | null>(null);
const cacheSize = ref<CacheSize | null>(null);
const recordSize = ref('-');
const loading = ref(false);

onMounted(() => {
  void loadHistory();
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
    recordSize.value = '-';
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载任务详情失败');
  }
}

async function loadRecordSize(recordId: string) {
  try {
    const result = await apiPost<{ success: boolean; size_formatted: string }>('/api/history/size', {
      record_id: recordId
    });
    recordSize.value = result.size_formatted;
  } catch (error) {
    message.error(error instanceof Error ? error.message : '计算目录占用失败');
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
    message.success('已清空历史记录');
    await loadHistory();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '清空失败');
  }
}

function statusType(status: string): TagProps['type'] {
  if (status === 'completed') return 'success';
  if (status === 'failed') return 'error';
  if (status === 'processing') return 'info';
  return 'default';
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

function recordSummary(record: HistoryRecord): string {
  return `${formatDate(record.timestamp)} / ${record.file_count} 个文件 / ${formatElapsed(record.elapsed_time)}`;
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

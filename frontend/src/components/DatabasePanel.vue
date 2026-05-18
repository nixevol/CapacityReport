<template>
  <div class="database-workspace">
    <aside class="database-sidebar-pane">
      <section class="database-table-pane">
        <div class="database-table-list-wrap">
          <n-empty v-if="tables.length === 0 && !loadingTables" description="暂无数据表" />
          <n-spin v-else-if="loadingTables" class="database-list-loading" size="small" />
          <n-scrollbar v-else class="database-table-list">
            <button
              v-for="table in tables"
              :key="table"
              type="button"
              class="database-table-item"
              :class="{ active: selectedTable === table }"
              @click="loadTable(table)"
            >
              <span class="table-dot"></span>
              <span class="table-name">{{ table }}</span>
            </button>
          </n-scrollbar>
        </div>
      </section>

      <section class="database-server-info">
        <div class="server-info-item">
          <span class="info-label">版本:</span>
          <span class="info-value">
            <span class="status-badge" :class="databaseInfo?.success ? 'success' : 'unknown'">
              {{ databaseInfo?.version || '检测中' }}
            </span>
          </span>
        </div>
        <div class="server-info-item">
          <span class="info-label">快速导入:</span>
          <span class="info-value">
            <button
              type="button"
              class="status-badge status-action"
              :class="loadDataInfileClass"
              :disabled="testing"
              aria-label="刷新快速导入状态"
              title="刷新快速导入状态"
              @click="testConnection"
            >
              {{ loadDataInfileText }}
            </button>
          </span>
        </div>
      </section>
    </aside>

    <section class="database-content-pane">
      <div v-if="selectedTable" class="database-toolbar">
        <div class="toolbar-left">
          <span class="current-table">{{ selectedTable }}</span>
          <span class="row-count">共 {{ total }} 条</span>
        </div>
        <n-space size="small" class="toolbar-actions">
          <n-button size="small" tertiary :loading="loadingData" @click="reloadTable">刷新</n-button>
          <n-button size="small" tertiary @click="downloadTable('csv')">CSV</n-button>
          <n-button size="small" tertiary @click="downloadTable('xlsx')">XLSX</n-button>
          <n-button size="small" tertiary type="warning" @click="confirmTruncate">清空</n-button>
          <n-button size="small" tertiary type="error" @click="confirmDrop">删除</n-button>
        </n-space>
      </div>

      <div class="database-data-body" :class="{ empty: !selectedTable }">
        <n-empty v-if="!selectedTable" description="请选择左侧的数据表" />
        <template v-else>
          <n-data-table
            size="small"
            class="database-data-table"
            :columns="columns"
            :data="rows"
            :loading="loadingData"
            :bordered="false"
            :single-line="false"
            flex-height
          />

          <n-collapse v-if="tableInfo" class="columns-collapse">
            <n-collapse-item title="字段结构" name="columns">
              <n-table size="small" :bordered="false">
                <thead>
                  <tr>
                    <th>字段</th>
                    <th>类型</th>
                    <th>允许空</th>
                    <th>键</th>
                    <th>默认值</th>
                    <th>备注</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="column in tableInfo.columns" :key="String(column.Field)">
                    <td>{{ column.Field }}</td>
                    <td>{{ column.Type }}</td>
                    <td>{{ column.Null }}</td>
                    <td>{{ column.Key }}</td>
                    <td>{{ column.Default ?? '' }}</td>
                    <td>{{ column.Extra }}</td>
                  </tr>
                </tbody>
              </n-table>
            </n-collapse-item>
          </n-collapse>
        </template>
      </div>

      <div v-if="selectedTable" class="database-pagination">
        <span class="pagination-total">共 {{ total }} 条</span>
        <n-pagination
          :page="page"
          :page-count="totalPages"
          :page-size="pageSize"
          show-size-picker
          :page-sizes="[20, 50, 100, 200]"
          @update:page="changePage"
          @update:page-size="changePageSize"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useDialog, useMessage } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import { TrashOutline } from '@vicons/ionicons5';

import { apiGet, apiPost, download } from '../api/client';
import type { ApiMessage, DatabaseInfo, TableData, TableInfo } from '../types';
import { resetPageHeader, setPageHeader } from '../composables/pageHeader';

type RowData = Record<string, unknown>;
type DownloadFormat = 'csv' | 'xlsx';

const message = useMessage();
const dialog = useDialog();
const databaseInfo = ref<DatabaseInfo | null>(null);
const tables = ref<string[]>([]);
const selectedTable = ref<string | null>(null);
const tableInfo = ref<TableInfo | null>(null);
const rows = ref<RowData[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(50);
const loadingTables = ref(false);
const loadingData = ref(false);
const testing = ref(false);

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)));
const loadDataInfileText = computed(() => {
  if (testing.value || !databaseInfo.value) return '检测中';
  return databaseInfo.value.load_data_infile ? '可用' : '未启用';
});
const loadDataInfileClass = computed(() => {
  if (testing.value || !databaseInfo.value) return 'unknown';
  return databaseInfo.value.load_data_infile ? 'success' : 'warning';
});
const columns = computed<DataTableColumns<RowData>>(() => {
  const keys = rows.value.length
    ? Object.keys(rows.value[0])
    : tableInfo.value?.columns.map(column => String(column.Field || '')).filter(Boolean) || [];

  return keys.map(key => ({
    title: key,
    key,
    minWidth: 120,
    ellipsis: { tooltip: true },
    render: row => formatCell(row[key])
  }));
});

onMounted(() => {
  setPageHeader({
    actions: [
      {
        key: 'drop-all-tables',
        label: '删除全部表',
        icon: TrashOutline,
        type: 'error',
        variant: 'solid',
        disabled: computed(() => tables.value.length === 0),
        onClick: confirmDropAll
      }
    ]
  });
  void testConnection();
  void loadTables();
});

onBeforeUnmount(() => {
  resetPageHeader();
});

async function testConnection() {
  testing.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/database/test');
    if (!result.success) {
      message.error(result.message || '数据库连接测试失败');
    }
    databaseInfo.value = await apiGet<DatabaseInfo>('/api/database/info');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '数据库连接测试失败');
  } finally {
    testing.value = false;
  }
}

async function loadTables() {
  loadingTables.value = true;
  try {
    const result = await apiGet<{ tables: string[] }>('/api/database/tables');
    tables.value = result.tables;
    if (selectedTable.value && !tables.value.includes(selectedTable.value)) {
      selectedTable.value = null;
      tableInfo.value = null;
      rows.value = [];
      total.value = 0;
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载数据表失败');
  } finally {
    loadingTables.value = false;
  }
}

async function loadTable(table: string) {
  selectedTable.value = table;
  page.value = 1;
  await Promise.all([loadTableInfo(table), loadTableData()]);
}

async function reloadTable() {
  if (!selectedTable.value) return;
  await Promise.all([loadTableInfo(selectedTable.value), loadTableData()]);
}

async function loadTableInfo(table: string) {
  try {
    tableInfo.value = await apiPost<TableInfo>('/api/database/table/info', { table_name: table });
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载表结构失败');
  }
}

async function loadTableData() {
  if (!selectedTable.value) return;
  loadingData.value = true;
  try {
    const result = await apiPost<TableData>('/api/database/table/data', {
      table_name: selectedTable.value,
      page: page.value,
      page_size: pageSize.value
    });
    rows.value = result.data;
    total.value = result.total;
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载表数据失败');
  } finally {
    loadingData.value = false;
  }
}

function changePage(value: number) {
  page.value = value;
  void loadTableData();
}

function changePageSize(value: number) {
  pageSize.value = value;
  page.value = 1;
  void loadTableData();
}

async function downloadTable(format: DownloadFormat) {
  if (!selectedTable.value) return;
  try {
    await download('/api/download', { table_name: selectedTable.value, format }, `${selectedTable.value}.${format}`);
  } catch (error) {
    message.error(error instanceof Error ? error.message : '导出失败');
  }
}

function confirmTruncate() {
  if (!selectedTable.value) return;
  dialog.warning({
    title: '清空数据表',
    content: `确认清空 ${selectedTable.value} 的全部数据？`,
    positiveText: '清空',
    negativeText: '取消',
    onPositiveClick: truncateTable
  });
}

async function truncateTable() {
  if (!selectedTable.value) return;
  try {
    await apiPost('/api/database/table/truncate', { table_name: selectedTable.value });
    message.success('数据表已清空');
    await reloadTable();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '清空失败');
  }
}

function confirmDrop() {
  if (!selectedTable.value) return;
  dialog.error({
    title: '删除数据表',
    content: `确认删除数据表 ${selectedTable.value}？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: dropTable
  });
}

async function dropTable() {
  if (!selectedTable.value) return;
  try {
    await apiPost('/api/database/table/drop', { table_name: selectedTable.value });
    message.success('数据表已删除');
    selectedTable.value = null;
    tableInfo.value = null;
    rows.value = [];
    total.value = 0;
    await loadTables();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '删除失败');
  }
}

function confirmDropAll() {
  if (tables.value.length === 0) return;
  dialog.error({
    title: '删除全部数据表',
    content: `确认删除当前数据库中的全部 ${tables.value.length} 张数据表？`,
    positiveText: '删除全部',
    negativeText: '取消',
    onPositiveClick: dropAllTables
  });
}

async function dropAllTables() {
  try {
    const result = await apiPost<ApiMessage & { dropped_count?: number }>('/api/database/table/drop-all');
    message.success(result.message || `已删除 ${result.dropped_count || 0} 张表`);
    selectedTable.value = null;
    tableInfo.value = null;
    rows.value = [];
    total.value = 0;
    await loadTables();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '删除全部数据表失败');
  }
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}
</script>

<style scoped>
.database-workspace {
  display: flex;
  gap: 20px;
  height: 100%;
  min-height: 0;
  min-width: 0;
  padding: 24px 32px;
}

.database-sidebar-pane {
  display: flex;
  flex: 0 0 240px;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.database-table-pane,
.database-content-pane,
.database-server-info {
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-border-color-light);
  border-radius: var(--td-radius-default);
}

.database-table-pane {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
}

.database-table-list-wrap {
  display: flex;
  flex: 1;
  min-height: 0;
  align-items: stretch;
  justify-content: center;
}

.database-list-loading {
  align-self: center;
}

.database-table-list {
  width: 100%;
  height: 100%;
}

.database-table-item {
  display: flex;
  width: 100%;
  min-height: 38px;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  color: var(--td-text-color-primary);
  font: inherit;
  text-align: left;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--td-border-color-light);
  cursor: pointer;
  transition: all var(--td-transition);
}

.database-table-item:hover {
  background: var(--td-bg-color-container-hover);
}

.database-table-item.active {
  color: var(--td-brand-color);
  font-weight: 500;
  background: var(--td-brand-color-light);
}

.table-dot {
  width: 7px;
  height: 7px;
  flex: 0 0 auto;
  background: var(--td-text-color-placeholder);
  border-radius: 50%;
}

.database-table-item.active .table-dot {
  background: var(--td-brand-color);
}

.table-name {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.database-server-info {
  position: relative;
  flex-shrink: 0;
  padding: 10px 12px;
  font-size: 12px;
  background: var(--td-bg-color-secondarycontainer);
}

.server-info-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 28px;
  gap: 10px;
}

.server-info-item:not(:last-of-type) {
  border-bottom: 1px dashed var(--td-border-color-light);
}

.info-label {
  color: var(--td-text-color-secondary);
}

.info-value {
  min-width: 84px;
  text-align: right;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  max-width: 112px;
  overflow: hidden;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 500;
  font-family: inherit;
  line-height: 18px;
  white-space: nowrap;
  text-overflow: ellipsis;
  border: 0;
  border-radius: 10px;
}

.status-action {
  cursor: pointer;
  transition: opacity var(--td-transition), box-shadow var(--td-transition), transform var(--td-transition);
}

.status-action:hover:not(:disabled) {
  box-shadow: inset 0 0 0 1px currentColor;
}

.status-action:active:not(:disabled) {
  transform: translateY(1px);
}

.status-action:disabled {
  cursor: wait;
  opacity: 0.78;
}

.status-badge.success {
  color: var(--td-success-color);
  background: var(--td-success-color-light);
}

.status-badge.warning {
  color: var(--td-warning-color);
  background: var(--td-warning-color-light);
}

.status-badge.unknown {
  color: var(--td-text-color-placeholder);
  background: var(--td-bg-color-container-hover);
}

.database-content-pane {
  display: flex;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  flex-direction: column;
}

.database-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 48px;
  padding: 12px 16px;
  background: var(--td-bg-color-secondarycontainer);
  border-bottom: 1px solid var(--td-border-color-light);
}

.toolbar-left {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 10px;
}

.current-table {
  overflow: hidden;
  max-width: 42vw;
  color: var(--td-text-color-primary);
  font-weight: 600;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.row-count {
  flex: 0 0 auto;
  padding: 2px 8px;
  color: var(--td-text-color-secondary);
  font-size: 12px;
  background: var(--td-bg-color-component);
  border-radius: 10px;
}

.toolbar-actions {
  flex: 0 0 auto;
}

.database-data-body {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: auto;
  flex-direction: column;
}

.database-data-body.empty {
  align-items: center;
  justify-content: center;
}

.database-data-table {
  flex: 1;
  min-height: 0;
}

.columns-collapse {
  flex: 0 0 auto;
  padding: 0 14px 12px;
  border-top: 1px solid var(--td-border-color-light);
}

.database-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 48px;
  padding: 12px 16px;
  background: var(--td-bg-color-secondarycontainer);
  border-top: 1px solid var(--td-border-color-light);
}

.pagination-total {
  flex: 0 0 auto;
  color: var(--td-text-color-secondary);
  font-size: 13px;
}

@media (max-width: 1180px) {
  .database-workspace {
    flex-direction: column;
    height: auto;
    min-height: 0;
    padding: 16px;
  }

  .database-sidebar-pane {
    flex: none;
    width: 100%;
    flex-direction: row;
  }

  .database-table-pane {
    min-height: 240px;
  }

  .database-server-info {
    flex: 0 0 240px;
  }

  .database-content-pane {
    min-height: 560px;
  }
}

@media (max-width: 720px) {
  .database-sidebar-pane {
    flex-direction: column;
  }

  .database-server-info {
    flex: none;
  }

  .database-toolbar,
  .database-pagination {
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar-actions {
    width: 100%;
  }
}
</style>

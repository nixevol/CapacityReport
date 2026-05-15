<template>
  <n-grid :cols="12" :x-gap="16" :y-gap="16" responsive="screen">
    <n-gi :span="12" :m="4">
      <n-space vertical size="large">
        <n-card title="数据库连接" size="small">
          <template #header-extra>
            <n-button size="small" tertiary :loading="testing" @click="testConnection">测试</n-button>
          </template>
          <n-space vertical>
            <n-alert v-if="databaseInfo" :type="databaseInfo.success ? 'success' : 'error'" :bordered="false">
              MySQL {{ databaseInfo.version || '-' }} / LOAD DATA:
              {{ databaseInfo.load_data_infile ? '可用' : '不可用' }}
            </n-alert>
            <n-button block :loading="loadingTables" @click="loadTables">刷新数据表</n-button>
          </n-space>
        </n-card>

        <n-card title="数据表" size="small">
          <template #header-extra>
            <n-button size="small" tertiary type="error" :disabled="tables.length === 0" @click="confirmDropAll">
              删除全部
            </n-button>
          </template>

          <n-space vertical>
            <n-select
              v-model:value="selectedTable"
              filterable
              clearable
              placeholder="选择数据表"
              :options="tableOptions"
              @update:value="handleSelectTable"
            />
            <n-empty v-if="tables.length === 0 && !loadingTables" description="暂无数据表" />
            <n-scrollbar v-else class="table-list">
              <n-list bordered>
                <n-list-item v-for="table in tables" :key="table">
                  <n-button text @click="loadTable(table)">{{ table }}</n-button>
                </n-list-item>
              </n-list>
            </n-scrollbar>
          </n-space>
        </n-card>
      </n-space>
    </n-gi>

    <n-gi :span="12" :m="8">
      <n-card title="表数据" size="small">
        <template #header-extra>
          <n-space>
            <n-button size="small" tertiary :disabled="!selectedTable" @click="reloadTable">刷新</n-button>
            <n-button size="small" tertiary :disabled="!selectedTable" @click="downloadTable('csv')">CSV</n-button>
            <n-button size="small" tertiary :disabled="!selectedTable" @click="downloadTable('xlsx')">XLSX</n-button>
            <n-button size="small" tertiary type="warning" :disabled="!selectedTable" @click="confirmTruncate">
              清空
            </n-button>
            <n-button size="small" tertiary type="error" :disabled="!selectedTable" @click="confirmDrop">
              删除
            </n-button>
          </n-space>
        </template>

        <n-empty v-if="!selectedTable" description="请选择数据表" />
        <n-space v-else vertical size="large">
          <n-descriptions v-if="tableInfo" bordered size="small" :column="3">
            <n-descriptions-item label="表名">{{ tableInfo.name }}</n-descriptions-item>
            <n-descriptions-item label="行数">{{ tableInfo.row_count }}</n-descriptions-item>
            <n-descriptions-item label="字段数">{{ tableInfo.columns.length }}</n-descriptions-item>
          </n-descriptions>

          <n-data-table
            size="small"
            :columns="columns"
            :data="rows"
            :loading="loadingData"
            :bordered="false"
            :single-line="false"
            max-height="420"
          />
          <div class="table-footer">
            <span>共 {{ total }} 行</span>
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

          <n-collapse v-if="tableInfo">
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
        </n-space>
      </n-card>
    </n-gi>
  </n-grid>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useDialog, useMessage } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';

import { apiGet, apiPost, download } from '../api/client';
import type { ApiMessage, DatabaseInfo, TableData, TableInfo } from '../types';

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

const tableOptions = computed(() => tables.value.map(table => ({ label: table, value: table })));
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)));
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
  void testConnection();
  void loadTables();
});

async function testConnection() {
  testing.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/database/test');
    message[result.success ? 'success' : 'error'](result.message || '连接测试完成');
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
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载数据表失败');
  } finally {
    loadingTables.value = false;
  }
}

function handleSelectTable(value: string | null) {
  if (value) {
    void loadTable(value);
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
  dialog.error({
    title: '删除全部数据表',
    content: '确认删除当前数据库中的全部数据表？',
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

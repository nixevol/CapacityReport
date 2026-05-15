<template>
  <div class="settings-workspace">
    <div class="settings-column">
      <n-card title="数据库配置" size="small" class="work-card">
        <template #header-extra>
          <n-space>
            <n-button size="small" tertiary :loading="loading" @click="loadConfig">刷新</n-button>
            <n-button size="small" tertiary :loading="testingDb" @click="testDatabase">测试连接</n-button>
          </n-space>
        </template>

        <n-form label-placement="top">
          <n-grid :cols="12" :x-gap="12">
            <n-gi :span="8">
              <n-form-item label="主机地址">
                <n-input v-model:value="mysqlForm.host" placeholder="localhost" />
              </n-form-item>
            </n-gi>
            <n-gi :span="4">
              <n-form-item label="端口">
                <n-input-number v-model:value="mysqlForm.port" class="full-width" :min="1" :max="65535" />
              </n-form-item>
            </n-gi>
          </n-grid>
          <n-form-item label="数据库名">
            <n-input v-model:value="mysqlForm.dbname" placeholder="CapacityReport" />
          </n-form-item>
          <n-grid :cols="12" :x-gap="12">
            <n-gi :span="6">
              <n-form-item label="用户名">
                <n-input v-model:value="mysqlForm.user" placeholder="root" />
              </n-form-item>
            </n-gi>
            <n-gi :span="6">
              <n-form-item label="密码">
                <n-input v-model:value="mysqlForm.passwd" type="password" show-password-on="click" />
              </n-form-item>
            </n-gi>
          </n-grid>
          <div class="card-actions">
            <span class="muted-line">更新时间：{{ configUpdate || '-' }}</span>
            <n-button type="primary" :loading="savingMysql" @click="saveMysql">保存配置</n-button>
          </div>
        </n-form>
      </n-card>

      <n-card title="Sheet 过滤规则" size="small" class="work-card">
        <n-space vertical>
          <div class="filter-tags">
            <n-tag
              v-for="(filter, index) in sheetFilters"
              :key="`${filter}-${index}`"
              closable
              @close="removeSheetFilter(index)"
            >
              {{ filter }}
            </n-tag>
            <n-empty v-if="sheetFilters.length === 0" size="small" description="暂无过滤规则" />
          </div>
          <n-input-group>
            <n-input
              v-model:value="newSheetFilter"
              placeholder="输入需要跳过的 Sheet 关键词"
              @keydown.enter.prevent="addSheetFilter"
            />
            <n-button @click="addSheetFilter">添加</n-button>
          </n-input-group>
          <div class="card-actions">
            <span class="muted-line">匹配这些关键词的 Sheet 会跳过处理</span>
            <n-button type="primary" :loading="savingSheetFilter" @click="saveSheetFilter">保存规则</n-button>
          </div>
        </n-space>
      </n-card>

      <n-card title="登录密码" size="small" class="work-card">
        <n-form label-placement="top">
          <n-form-item label="当前密码">
            <n-input v-model:value="passwordForm.current_password" type="password" show-password-on="click" />
          </n-form-item>
          <n-form-item label="新密码">
            <n-input v-model:value="passwordForm.new_password" type="password" show-password-on="click" />
          </n-form-item>
          <n-form-item label="确认密码">
            <n-input v-model:value="passwordForm.confirm_password" type="password" show-password-on="click" />
          </n-form-item>
          <div class="card-actions">
            <span />
            <n-button type="primary" :loading="changingPassword" @click="changePassword">修改密码</n-button>
          </div>
        </n-form>
      </n-card>

      <n-card title="配置文件与服务" size="small" class="work-card">
        <n-space vertical>
          <n-space>
            <n-button @click="downloadConfig">下载配置</n-button>
            <n-button @click="configInput?.click()">上传配置</n-button>
            <input ref="configInput" class="hidden-input" type="file" accept=".json" @change="uploadConfigFile" />
          </n-space>

          <n-descriptions v-if="serviceStatus" bordered size="small" :column="2">
            <n-descriptions-item label="状态">{{ serviceStatus.status }}</n-descriptions-item>
            <n-descriptions-item label="版本">{{ serviceStatus.version }}</n-descriptions-item>
            <n-descriptions-item label="系统">{{ serviceStatus.platform }}</n-descriptions-item>
            <n-descriptions-item label="进程">{{ serviceStatus.pid }}</n-descriptions-item>
          </n-descriptions>

          <div class="card-actions">
            <n-button size="small" tertiary @click="loadServiceStatus">刷新状态</n-button>
            <n-button type="warning" tertiary @click="confirmRestart">重启服务</n-button>
          </div>
        </n-space>
      </n-card>
    </div>

    <n-card size="small" class="work-card field-mapping-card">
      <template #header>
        <div class="field-card-title">
          <span>字段提取配置</span>
          <n-tag size="small" round>{{ extractFields.length }} 个字段</n-tag>
        </div>
      </template>
      <template #header-extra>
        <n-space align="center">
          <n-input
            v-model:value="fieldSearch"
            size="small"
            clearable
            class="field-search"
            placeholder="搜索字段或提取来源"
          />
          <n-button size="small" @click="addFieldMapping">添加字段</n-button>
          <n-button size="small" type="primary" :loading="savingExtractFields" @click="saveExtractFields">
            保存映射
          </n-button>
        </n-space>
      </template>

      <n-scrollbar class="field-mapping-scroll">
        <n-empty v-if="visibleFieldMappings.length === 0" description="没有匹配的字段配置" />

        <div
          v-for="{ field, index } in visibleFieldMappings"
          :key="index"
          class="field-mapping-item"
        >
          <div class="field-mapping-number">{{ index + 1 }}</div>
          <n-button
            quaternary
            circle
            size="small"
            type="error"
            class="field-remove-button"
            @click="removeFieldMapping(index)"
          >
            ×
          </n-button>

          <div class="field-mapping-header">
            <n-form-item label="数据库字段名" class="field-name-control">
              <n-input v-model:value="field.Field" placeholder="输入字段名" />
            </n-form-item>
            <n-form-item label="字段类型" class="field-type-control">
              <n-select v-model:value="field.Type" :options="fieldTypeOptions" />
            </n-form-item>
          </div>

          <div class="extract-list">
            <div class="extract-list-header">
              <span>提取来源（{{ field.Extract.length }} 个）</span>
              <n-input-group class="extract-add-group">
                <n-input
                  v-model:value="newExtractValues[index]"
                  size="small"
                  placeholder="输入 Excel 列名"
                  @keydown.enter.prevent="addExtract(index)"
                />
                <n-button size="small" @click="addExtract(index)">添加</n-button>
              </n-input-group>
            </div>

            <div v-if="field.Extract.length > 0" class="extract-tree">
              <div v-for="(source, sourceIndex) in field.Extract" :key="`${source}-${sourceIndex}`" class="extract-tree-item">
                <span class="tree-text">{{ source }}</span>
                <n-button text size="tiny" type="warning" @click="removeExtract(index, sourceIndex)">删除</n-button>
              </div>
            </div>
            <div v-else class="extract-empty">暂无提取来源</div>
          </div>
        </div>
      </n-scrollbar>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useDialog, useMessage, type SelectOption } from 'naive-ui';

import { apiGet, apiPost, downloadGet, upload } from '../api/client';
import type { ApiMessage, AppConfig, ServiceStatus } from '../types';

interface ExtractFieldConfig {
  Field: string;
  Type: string;
  Extract: string[];
  [key: string]: unknown;
}

const message = useMessage();
const dialog = useDialog();
const configInput = ref<HTMLInputElement | null>(null);
const configUpdate = ref('');
const loading = ref(false);
const testingDb = ref(false);
const savingMysql = ref(false);
const savingSheetFilter = ref(false);
const savingExtractFields = ref(false);
const changingPassword = ref(false);
const serviceStatus = ref<ServiceStatus | null>(null);
const sheetFilters = ref<string[]>([]);
const newSheetFilter = ref('');
const extractFields = ref<ExtractFieldConfig[]>([]);
const fieldSearch = ref('');
const newExtractValues = reactive<Record<number, string>>({});

const mysqlForm = reactive({
  host: '',
  port: 3306 as number | null,
  user: '',
  passwd: '',
  dbname: ''
});

const passwordForm = reactive({
  current_password: '',
  new_password: '',
  confirm_password: ''
});

const fieldTypeOptions: SelectOption[] = [
  { label: '字符串', value: 'string' },
  { label: '整数', value: 'int' },
  { label: '小数', value: 'float' },
  { label: '日期时间', value: 'datetime' }
];

const visibleFieldMappings = computed(() => {
  const keyword = fieldSearch.value.trim().toLowerCase();
  return extractFields.value
    .map((field, index) => ({ field, index }))
    .filter(({ field }) => {
      if (!keyword) return true;
      const fieldName = field.Field.toLowerCase();
      const extractText = field.Extract.join(' ').toLowerCase();
      return fieldName.includes(keyword) || extractText.includes(keyword);
    });
});

onMounted(() => {
  void loadConfig();
  void loadServiceStatus();
});

async function loadConfig() {
  loading.value = true;
  try {
    const config = await apiGet<AppConfig>('/api/config/full');
    configUpdate.value = config.update;
    mysqlForm.host = config.mysql.host;
    mysqlForm.port = config.mysql.port;
    mysqlForm.user = config.mysql.user;
    mysqlForm.passwd = config.mysql.passwd || '';
    mysqlForm.dbname = config.mysql.dbname;
    sheetFilters.value = [...config.sheet_filter];
    extractFields.value = normalizeExtractFields(config.extract_fields);
    resetExtractInputs();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载配置失败');
  } finally {
    loading.value = false;
  }
}

async function saveMysql() {
  if (!mysqlForm.host || !mysqlForm.user || !mysqlForm.dbname) {
    message.warning('请填写完整数据库配置');
    return;
  }

  savingMysql.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/mysql', {
      ...mysqlForm,
      port: mysqlForm.port || 3306
    });
    configUpdate.value = result.update || configUpdate.value;
    message.success(result.message || '数据库配置已保存');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存数据库配置失败');
  } finally {
    savingMysql.value = false;
  }
}

async function testDatabase() {
  testingDb.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/database/test');
    message[result.success ? 'success' : 'error'](result.message || '连接测试完成');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '数据库连接测试失败');
  } finally {
    testingDb.value = false;
  }
}

function addSheetFilter() {
  const value = newSheetFilter.value.trim();
  if (!value) return;
  if (sheetFilters.value.includes(value)) {
    message.warning('该规则已存在');
    return;
  }
  sheetFilters.value.push(value);
  newSheetFilter.value = '';
}

function removeSheetFilter(index: number) {
  sheetFilters.value.splice(index, 1);
}

async function saveSheetFilter() {
  savingSheetFilter.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/sheet-filter', sheetFilters.value);
    configUpdate.value = result.update || configUpdate.value;
    message.success(result.message || '过滤规则已保存');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存过滤规则失败');
  } finally {
    savingSheetFilter.value = false;
  }
}

function addFieldMapping() {
  extractFields.value.push({ Field: '', Type: 'string', Extract: [] });
  resetExtractInputs();
}

function removeFieldMapping(index: number) {
  extractFields.value.splice(index, 1);
  resetExtractInputs();
}

function addExtract(index: number) {
  const value = (newExtractValues[index] || '').trim();
  if (!value) return;

  const field = extractFields.value[index];
  if (!field) return;

  if (field.Extract.includes(value)) {
    message.warning('该提取来源已存在');
    return;
  }

  field.Extract.push(value);
  newExtractValues[index] = '';
}

function removeExtract(fieldIndex: number, extractIndex: number) {
  extractFields.value[fieldIndex]?.Extract.splice(extractIndex, 1);
}

async function saveExtractFields() {
  const fields = extractFields.value
    .map(field => ({
      ...field,
      Field: field.Field.trim(),
      Type: field.Type || 'string',
      Extract: uniqueStrings(field.Extract)
    }))
    .filter(field => field.Field);

  if (fields.length === 0) {
    message.warning('请至少保留一个有效字段');
    return;
  }

  savingExtractFields.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/extract-fields', fields);
    extractFields.value = fields;
    resetExtractInputs();
    configUpdate.value = result.update || configUpdate.value;
    message.success(result.message || '字段配置已保存');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存字段配置失败');
  } finally {
    savingExtractFields.value = false;
  }
}

async function changePassword() {
  if (passwordForm.new_password.length < 4) {
    message.warning('新密码不能少于 4 位');
    return;
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    message.warning('两次输入的新密码不一致');
    return;
  }

  changingPassword.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/change-password', {
      current_password: passwordForm.current_password,
      new_password: passwordForm.new_password
    });
    passwordForm.current_password = '';
    passwordForm.new_password = '';
    passwordForm.confirm_password = '';
    message.success(result.message || '密码已修改');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '修改密码失败');
  } finally {
    changingPassword.value = false;
  }
}

async function downloadConfig() {
  try {
    await downloadGet('/api/config/download', 'Configure.json');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '下载配置失败');
  }
}

async function uploadConfigFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);
  try {
    const result = await upload<ApiMessage>('/api/config/upload', formData);
    message.success(result.message || '配置文件已上传');
    await loadConfig();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '上传配置失败');
  }
}

async function loadServiceStatus() {
  try {
    serviceStatus.value = await apiGet<ServiceStatus>('/api/service/status');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '读取运行状态失败');
  }
}

function confirmRestart() {
  dialog.warning({
    title: '重启服务',
    content: '确认重启后端服务？',
    positiveText: '重启',
    negativeText: '取消',
    onPositiveClick: restartService
  });
}

async function restartService() {
  try {
    const result = await apiPost<ApiMessage>('/api/service/restart');
    message.success(result.message || '服务正在重启');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '重启服务失败');
  }
}

function normalizeExtractFields(fields: Array<Record<string, unknown>>): ExtractFieldConfig[] {
  return fields.map(field => {
    const extract = Array.isArray(field.Extract) ? uniqueStrings(field.Extract) : [];
    return {
      ...field,
      Field: String(field.Field || ''),
      Type: typeof field.Type === 'string' && field.Type ? field.Type : 'string',
      Extract: extract
    };
  });
}

function uniqueStrings(values: unknown[]): string[] {
  return Array.from(
    new Set(
      values
        .map(value => String(value || '').trim())
        .filter(Boolean)
    )
  );
}

function resetExtractInputs() {
  for (const key of Object.keys(newExtractValues)) {
    delete newExtractValues[Number(key)];
  }
  extractFields.value.forEach((_, index) => {
    newExtractValues[index] = '';
  });
}
</script>

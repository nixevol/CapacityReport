<template>
  <n-grid :cols="12" :x-gap="16" :y-gap="16" responsive="screen">
    <n-gi :span="12" :m="6">
      <n-space vertical size="large">
        <n-card title="数据库配置" size="small">
          <template #header-extra>
            <n-button size="small" tertiary :loading="loading" @click="loadConfig">刷新</n-button>
          </template>
          <n-form label-placement="left" label-width="90">
            <n-form-item label="地址">
              <n-input v-model:value="mysqlForm.host" />
            </n-form-item>
            <n-form-item label="端口">
              <n-input-number v-model:value="mysqlForm.port" class="full-width" :min="1" :max="65535" />
            </n-form-item>
            <n-form-item label="账号">
              <n-input v-model:value="mysqlForm.user" />
            </n-form-item>
            <n-form-item label="密码">
              <n-input v-model:value="mysqlForm.passwd" type="password" show-password-on="click" />
            </n-form-item>
            <n-form-item label="库名">
              <n-input v-model:value="mysqlForm.dbname" />
            </n-form-item>
            <n-button type="primary" :loading="savingMysql" @click="saveMysql">保存数据库配置</n-button>
          </n-form>
          <div class="muted-line">配置更新时间：{{ configUpdate || '-' }}</div>
        </n-card>

        <n-card title="登录密码" size="small">
          <n-form label-placement="left" label-width="90">
            <n-form-item label="当前密码">
              <n-input v-model:value="passwordForm.current_password" type="password" show-password-on="click" />
            </n-form-item>
            <n-form-item label="新密码">
              <n-input v-model:value="passwordForm.new_password" type="password" show-password-on="click" />
            </n-form-item>
            <n-form-item label="确认密码">
              <n-input v-model:value="passwordForm.confirm_password" type="password" show-password-on="click" />
            </n-form-item>
            <n-button type="primary" :loading="changingPassword" @click="changePassword">修改密码</n-button>
          </n-form>
        </n-card>

        <n-card title="配置文件" size="small">
          <n-space>
            <n-button @click="downloadConfig">下载配置</n-button>
            <n-button @click="configInput?.click()">上传配置</n-button>
            <input ref="configInput" class="hidden-input" type="file" accept=".json" @change="uploadConfigFile" />
          </n-space>
        </n-card>
      </n-space>
    </n-gi>

    <n-gi :span="12" :m="6">
      <n-space vertical size="large">
        <n-card title="Sheet 过滤规则" size="small">
          <n-space vertical>
            <n-input
              v-model:value="sheetFilterText"
              type="textarea"
              :autosize="{ minRows: 6, maxRows: 10 }"
              placeholder="每行一条规则"
            />
            <n-button type="primary" :loading="savingSheetFilter" @click="saveSheetFilter">保存过滤规则</n-button>
          </n-space>
        </n-card>

        <n-card title="字段提取配置" size="small">
          <n-space vertical>
            <n-input
              v-model:value="extractFieldsText"
              type="textarea"
              class="json-editor"
              :autosize="{ minRows: 12, maxRows: 18 }"
              spellcheck="false"
            />
            <n-space>
              <n-button :disabled="!extractFieldsText" @click="formatExtractFields">格式化</n-button>
              <n-button type="primary" :loading="savingExtractFields" @click="saveExtractFields">
                保存字段配置
              </n-button>
            </n-space>
          </n-space>
        </n-card>

        <n-card title="运行状态" size="small">
          <template #header-extra>
            <n-button size="small" tertiary @click="loadServiceStatus">刷新</n-button>
          </template>
          <n-descriptions v-if="serviceStatus" bordered size="small" :column="2">
            <n-descriptions-item label="状态">{{ serviceStatus.status }}</n-descriptions-item>
            <n-descriptions-item label="版本">{{ serviceStatus.version }}</n-descriptions-item>
            <n-descriptions-item label="系统">{{ serviceStatus.platform }}</n-descriptions-item>
            <n-descriptions-item label="进程">{{ serviceStatus.pid }}</n-descriptions-item>
            <n-descriptions-item label="Python">{{ serviceStatus.python_version }}</n-descriptions-item>
            <n-descriptions-item label="Supervisor">{{ serviceStatus.supervisor ? '是' : '否' }}</n-descriptions-item>
          </n-descriptions>
          <n-button class="restart-button" type="warning" tertiary @click="confirmRestart">重启服务</n-button>
        </n-card>
      </n-space>
    </n-gi>
  </n-grid>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useDialog, useMessage } from 'naive-ui';

import { apiGet, apiPost, downloadGet, upload } from '../api/client';
import type { ApiMessage, AppConfig, ServiceStatus } from '../types';

const message = useMessage();
const dialog = useDialog();
const configInput = ref<HTMLInputElement | null>(null);
const configUpdate = ref('');
const loading = ref(false);
const savingMysql = ref(false);
const savingSheetFilter = ref(false);
const savingExtractFields = ref(false);
const changingPassword = ref(false);
const sheetFilterText = ref('');
const extractFieldsText = ref('[]');
const serviceStatus = ref<ServiceStatus | null>(null);

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
    sheetFilterText.value = config.sheet_filter.join('\n');
    extractFieldsText.value = JSON.stringify(config.extract_fields, null, 2);
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

async function saveSheetFilter() {
  savingSheetFilter.value = true;
  try {
    const filters = sheetFilterText.value
      .split(/\r?\n/)
      .map(item => item.trim())
      .filter(Boolean);
    const result = await apiPost<ApiMessage>('/api/config/sheet-filter', filters);
    configUpdate.value = result.update || configUpdate.value;
    message.success(result.message || '过滤规则已保存');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存过滤规则失败');
  } finally {
    savingSheetFilter.value = false;
  }
}

function formatExtractFields() {
  try {
    extractFieldsText.value = JSON.stringify(JSON.parse(extractFieldsText.value), null, 2);
  } catch {
    message.error('字段配置不是有效 JSON');
  }
}

async function saveExtractFields() {
  let fields: Array<Record<string, unknown>>;
  try {
    const parsed = JSON.parse(extractFieldsText.value) as unknown;
    if (!Array.isArray(parsed)) {
      throw new Error('字段配置必须是数组');
    }
    fields = parsed as Array<Record<string, unknown>>;
  } catch (error) {
    message.error(error instanceof Error ? error.message : '字段配置不是有效 JSON');
    return;
  }

  savingExtractFields.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/extract-fields', fields);
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
</script>

<template>
  <div class="api-token-manager" :class="{ embedded }">
    <n-card size="small" class="work-card api-token-card" title="API Token">
      <template #header-extra>
        <n-space size="small">
          <n-button size="small" type="primary" @click="openCreateDialog">
            <template #icon><n-icon><AddOutline /></n-icon></template>
            生成 Token
          </n-button>
          <n-button size="small" tertiary :loading="loadingTokens" @click="loadTokens">
            <template #icon><n-icon><RefreshOutline /></n-icon></template>
            刷新
          </n-button>
        </n-space>
      </template>

      <div class="api-token-intro">
        API Token 用于内网程序直接调用业务接口。完整 Token 只会在生成或重生成时显示一次，请立即复制保存。
      </div>

      <n-spin v-if="loadingTokens" class="api-token-loading" />
      <n-empty v-else-if="tokens.length === 0" description="暂无 API Token" />
      <n-scrollbar v-else class="api-token-list">
        <div v-for="token in tokens" :key="token.id" class="api-token-item">
          <div class="api-token-main">
            <div class="api-token-title-row">
              <span class="api-token-name">{{ token.name }}</span>
              <n-tag size="small" :type="token.enabled && !token.expired ? 'success' : 'warning'">
                {{ tokenStatusText(token) }}
              </n-tag>
            </div>
            <div class="api-token-mask monospace">{{ token.prefix }}...{{ token.suffix }}</div>
            <div class="api-token-meta">
              <span>到期：{{ formatExpiration(token.expires_at) }}</span>
              <span>最近使用：{{ formatDateTime(token.last_used_at) }}</span>
              <span v-if="token.last_used_from">来源：{{ token.last_used_from }}</span>
            </div>
          </div>
          <div class="api-token-actions">
            <n-button size="tiny" tertiary @click="openEditDialog(token)">编辑</n-button>
            <n-button size="tiny" tertiary type="warning" @click="confirmRegenerate(token)">重生成</n-button>
            <n-button size="tiny" tertiary type="error" @click="confirmDelete(token)">删除</n-button>
          </div>
        </div>
      </n-scrollbar>
    </n-card>

    <n-modal
      v-model:show="tokenDialogVisible"
      preset="card"
      :title="editingToken ? '编辑 Token' : '生成 Token'"
      :style="{ width: '440px', maxWidth: 'calc(100vw - 32px)' }"
      :mask-closable="!savingToken"
    >
      <n-form label-placement="top">
        <n-form-item label="名称">
          <n-input v-model:value="tokenForm.name" placeholder="例如：外部系统接入" />
        </n-form-item>
        <n-form-item label="有效期">
          <n-radio-group v-model:value="tokenForm.permanent">
            <n-space>
              <n-radio :value="true">永久有效</n-radio>
              <n-radio :value="false">指定日期</n-radio>
            </n-space>
          </n-radio-group>
        </n-form-item>
        <n-form-item v-if="!tokenForm.permanent" label="到期日期">
          <n-date-picker
            v-model:formatted-value="tokenForm.expires_at"
            type="date"
            value-format="yyyy-MM-dd"
            clearable
            class="full-width"
          />
        </n-form-item>
        <n-form-item label="启用">
          <n-switch v-model:value="tokenForm.enabled" />
        </n-form-item>
      </n-form>

      <template #footer>
        <div class="api-token-dialog-footer">
          <n-button :disabled="savingToken" @click="tokenDialogVisible = false">取消</n-button>
          <n-button type="primary" :loading="savingToken" @click="saveToken">
            {{ editingToken ? '保存' : '生成' }}
          </n-button>
        </div>
      </template>
    </n-modal>

    <n-modal
      v-model:show="rawTokenVisible"
      preset="card"
      title="Token 已生成"
      :style="{ width: '520px', maxWidth: 'calc(100vw - 32px)' }"
    >
      <n-alert type="warning" :bordered="false">
        这是唯一一次显示完整 Token，请立即复制并妥善保存。
      </n-alert>
      <n-input
        class="raw-token-input"
        :value="rawToken"
        type="textarea"
        readonly
        :autosize="{ minRows: 3, maxRows: 6 }"
      />
      <template #footer>
        <div class="api-token-dialog-footer">
          <n-button @click="rawTokenVisible = false">关闭</n-button>
          <n-button type="primary" @click="copyRawToken">复制 Token</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useDialog, useMessage } from 'naive-ui';
import { AddOutline, RefreshOutline } from '@vicons/ionicons5';

import { apiGet, apiPost } from '../api/client';
import type { ApiMessage, ApiTokenListResponse, ApiTokenMutationResponse, ApiTokenRecord } from '../types';

defineProps<{
  embedded?: boolean;
}>();

const message = useMessage();
const dialog = useDialog();
const tokens = ref<ApiTokenRecord[]>([]);
const loadingTokens = ref(false);
const savingToken = ref(false);
const tokenDialogVisible = ref(false);
const rawTokenVisible = ref(false);
const rawToken = ref('');
const editingToken = ref<ApiTokenRecord | null>(null);
const tokenForm = reactive({
  name: '',
  permanent: true,
  expires_at: '',
  enabled: true
});

onMounted(() => {
  void loadTokens();
});

async function loadTokens() {
  loadingTokens.value = true;
  try {
    const result = await apiGet<ApiTokenListResponse>('/api/tokens');
    tokens.value = result.tokens;
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载 Token 失败');
  } finally {
    loadingTokens.value = false;
  }
}

function openCreateDialog() {
  editingToken.value = null;
  tokenForm.name = '';
  tokenForm.permanent = true;
  tokenForm.expires_at = '';
  tokenForm.enabled = true;
  tokenDialogVisible.value = true;
}

function openEditDialog(token: ApiTokenRecord) {
  editingToken.value = token;
  tokenForm.name = token.name;
  tokenForm.permanent = !token.expires_at;
  tokenForm.expires_at = token.expires_at?.slice(0, 10) || '';
  tokenForm.enabled = token.enabled;
  tokenDialogVisible.value = true;
}

async function saveToken() {
  const payload = {
    id: editingToken.value?.id,
    name: tokenForm.name.trim(),
    permanent: tokenForm.permanent,
    expires_at: tokenForm.permanent ? null : tokenForm.expires_at,
    enabled: tokenForm.enabled
  };
  if (!payload.name) {
    message.warning('请输入 Token 名称');
    return;
  }
  if (!payload.permanent && !payload.expires_at) {
    message.warning('请选择到期日期');
    return;
  }

  savingToken.value = true;
  try {
    const result = editingToken.value
      ? await apiPost<ApiTokenMutationResponse>('/api/tokens/update', payload)
      : await apiPost<ApiTokenMutationResponse>('/api/tokens/create', payload);
    message.success(result.message || (editingToken.value ? 'Token 已更新' : 'Token 已生成'));
    tokenDialogVisible.value = false;
    if (result.token) {
      rawToken.value = result.token;
      rawTokenVisible.value = true;
    }
    await loadTokens();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存 Token 失败');
  } finally {
    savingToken.value = false;
  }
}

function confirmRegenerate(token: ApiTokenRecord) {
  dialog.warning({
    title: '重新生成 Token',
    content: `确认重新生成「${token.name}」吗？旧 Token 会立即失效。`,
    positiveText: '重新生成',
    negativeText: '取消',
    onPositiveClick: () => regenerateToken(token)
  });
}

async function regenerateToken(token: ApiTokenRecord) {
  try {
    const result = await apiPost<ApiTokenMutationResponse>('/api/tokens/regenerate', { id: token.id });
    rawToken.value = result.token || '';
    rawTokenVisible.value = Boolean(rawToken.value);
    message.success(result.message || 'Token 已重新生成');
    await loadTokens();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '重新生成 Token 失败');
  }
}

function confirmDelete(token: ApiTokenRecord) {
  dialog.error({
    title: '删除 Token',
    content: `确认删除「${token.name}」吗？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: () => deleteToken(token)
  });
}

async function deleteToken(token: ApiTokenRecord) {
  try {
    const result = await apiPost<ApiMessage>('/api/tokens/delete', { id: token.id });
    message.success(result.message || 'Token 已删除');
    await loadTokens();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '删除 Token 失败');
  }
}

async function copyRawToken() {
  await writeClipboard(rawToken.value);
  message.success('Token 已复制');
}

async function writeClipboard(text: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.top = '-1000px';
  document.body.appendChild(textarea);
  textarea.select();
  try {
    document.execCommand('copy');
  } finally {
    document.body.removeChild(textarea);
  }
}

function tokenStatusText(token: ApiTokenRecord): string {
  if (!token.enabled) return '已停用';
  if (token.expired) return '已过期';
  return '可用';
}

function formatExpiration(value: string | null): string {
  if (!value) return '永久有效';
  return value.replace('T', ' ').slice(0, 10);
}

function formatDateTime(value?: string | null): string {
  if (!value) return '-';
  return value.replace('T', ' ').slice(0, 19);
}
</script>

<style scoped>
.api-token-manager {
  min-height: 0;
}

.api-token-manager.embedded {
  height: 100%;
  min-height: 0;
}

.api-token-card {
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
}

.api-token-card > :deep(.n-card__content),
.api-token-card > :deep(.n-card-content) {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
}

.api-token-intro {
  margin-bottom: 12px;
  color: var(--td-text-color-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.api-token-loading {
  margin: 48px auto;
}

.api-token-list {
  flex: 1;
  min-height: 220px;
}

.api-token-item {
  display: flex;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--td-border-color-light);
}

.api-token-main {
  min-width: 0;
  flex: 1;
}

.api-token-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.api-token-name {
  min-width: 0;
  overflow: hidden;
  color: var(--td-text-color-primary);
  font-weight: 600;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.api-token-mask {
  margin-top: 6px;
  color: var(--td-text-color-secondary);
  font-family: var(--td-font-family-mono);
  font-size: 12px;
}

.api-token-meta {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-top: 8px;
  color: var(--td-text-color-placeholder);
  font-size: 12px;
}

.api-token-actions {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 6px;
}

.raw-token-input {
  margin-top: 12px;
}

.api-token-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 720px) {
  .api-token-item {
    flex-direction: column;
  }

  .api-token-actions {
    flex-direction: row;
  }
}
</style>

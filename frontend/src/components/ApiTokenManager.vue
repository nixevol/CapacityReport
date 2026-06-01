<template>
  <div class="api-token-manager" :class="{ embedded }">
    <n-card size="small" class="work-card api-token-card" title="API Token">
      <template #header-extra>
        <n-space size="small">
          <n-button
            v-if="selectedTokenIds.length > 0"
            size="small"
            tertiary
            type="error"
            :loading="batchDeleting"
            @click="confirmBatchDelete"
          >
            批量删除 {{ selectedTokenIds.length }}
          </n-button>
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
        API Token 用于内网程序直接调用业务接口。完整 Token 会保存到本地，可在列表中随时复制。
      </div>

      <n-spin v-if="loadingTokens" class="api-token-loading" />
      <n-empty v-else-if="tokens.length === 0" description="暂无 API Token" />
      <n-scrollbar v-else class="api-token-list">
        <div v-for="token in tokens" :key="token.id" class="api-token-item">
          <n-checkbox
            class="api-token-select"
            :checked="isTokenSelected(token.id)"
            @update:checked="setTokenSelected(token.id, $event)"
          />
          <div class="api-token-main">
            <div class="api-token-title-row">
              <span class="api-token-name">{{ token.name }}</span>
              <n-tag size="small" :type="token.enabled && !token.expired ? 'success' : 'warning'">
                {{ tokenStatusText(token) }}
              </n-tag>
            </div>
            <div class="api-token-value-row">
              <div class="api-token-value monospace">{{ tokenDisplayValue(token) }}</div>
              <div class="api-token-value-actions">
                <n-button
                  circle
                  quaternary
                  size="tiny"
                  :title="token.token ? (isTokenRevealed(token.id) ? '隐藏 Token' : '显示 Token') : '旧 Token 未保存完整值'"
                  :disabled="!token.token"
                  @click="toggleTokenVisibility(token)"
                >
                  <template #icon>
                    <n-icon>
                      <EyeOffOutline v-if="isTokenRevealed(token.id)" />
                      <EyeOutline v-else />
                    </n-icon>
                  </template>
                </n-button>
                <n-button
                  circle
                  quaternary
                  size="tiny"
                  title="复制 Token"
                  :disabled="!token.token"
                  @click="copyToken(token)"
                >
                  <template #icon><n-icon><CopyOutline /></n-icon></template>
                </n-button>
              </div>
            </div>
            <div class="api-token-meta">
              <span>创建：{{ formatDateTime(token.created_at) }}</span>
              <span>到期：{{ formatExpiration(token.expires_at) }}</span>
              <span>最近使用：{{ formatDateTime(token.last_used_at) }}</span>
              <span v-if="token.last_used_from">来源：{{ token.last_used_from }}</span>
            </div>
          </div>
          <div class="api-token-actions">
            <n-dropdown
              trigger="click"
              :options="tokenActionOptions(token)"
              @select="handleTokenAction(token, $event)"
            >
              <n-button size="tiny" tertiary>
                <template #icon><n-icon><ChevronDownOutline /></n-icon></template>
                操作
              </n-button>
            </n-dropdown>
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
          <n-radio-group v-model:value="tokenForm.permanent" @update:value="handlePermanentChange">
            <n-space>
              <n-radio :value="true">永久有效</n-radio>
              <n-radio :value="false">指定日期</n-radio>
            </n-space>
          </n-radio-group>
        </n-form-item>
        <n-form-item v-if="!tokenForm.permanent" label="到期日期">
          <input
            v-model="tokenForm.expires_at"
            class="api-token-date-input"
            type="date"
            :disabled="savingToken"
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
      <n-alert type="success" :bordered="false">
        完整 Token 已保存，可在列表中随时复制。请注意只在可信内网环境中使用。
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
import { useDialog, useMessage, type DropdownOption } from 'naive-ui';
import { AddOutline, ChevronDownOutline, CopyOutline, EyeOffOutline, EyeOutline, RefreshOutline } from '@vicons/ionicons5';

import { apiGet, apiPost } from '../api/client';
import { writeClipboardText } from '../composables/clipboard';
import type { ApiMessage, ApiTokenListResponse, ApiTokenMutationResponse, ApiTokenRecord } from '../types';

defineProps<{
  embedded?: boolean;
}>();

const message = useMessage();
const dialog = useDialog();
const tokens = ref<ApiTokenRecord[]>([]);
const loadingTokens = ref(false);
const savingToken = ref(false);
const batchDeleting = ref(false);
const tokenDialogVisible = ref(false);
const rawTokenVisible = ref(false);
const rawToken = ref('');
const editingToken = ref<ApiTokenRecord | null>(null);
const selectedTokenIds = ref<string[]>([]);
const visibleTokenIds = ref<string[]>([]);
const tokenForm = reactive({
  name: '',
  permanent: false,
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
    const tokenIds = new Set(tokens.value.map(token => token.id));
    selectedTokenIds.value = selectedTokenIds.value.filter(id => tokenIds.has(id));
    visibleTokenIds.value = visibleTokenIds.value.filter(id => tokenIds.has(id));
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载 Token 失败');
  } finally {
    loadingTokens.value = false;
  }
}

function openCreateDialog() {
  editingToken.value = null;
  tokenForm.name = '';
  tokenForm.permanent = false;
  tokenForm.expires_at = defaultExpirationDate();
  tokenForm.enabled = true;
  tokenDialogVisible.value = true;
}

function openEditDialog(token: ApiTokenRecord) {
  editingToken.value = token;
  tokenForm.name = token.name;
  tokenForm.permanent = !token.expires_at;
  tokenForm.expires_at = token.expires_at?.slice(0, 10) || defaultExpirationDate();
  tokenForm.enabled = token.enabled;
  tokenDialogVisible.value = true;
}

function handlePermanentChange(value: boolean) {
  tokenForm.permanent = value;
  if (!value && !tokenForm.expires_at) {
    tokenForm.expires_at = defaultExpirationDate();
  }
}

async function saveToken() {
  const expiresAt = tokenForm.expires_at || defaultExpirationDate();
  const payload = {
    id: editingToken.value?.id,
    name: tokenForm.name.trim(),
    permanent: tokenForm.permanent,
    expires_at: tokenForm.permanent ? null : expiresAt,
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

async function toggleTokenEnabled(token: ApiTokenRecord) {
  try {
    const result = await apiPost<ApiTokenMutationResponse>('/api/tokens/update', {
      id: token.id,
      name: token.name,
      permanent: !token.expires_at,
      expires_at: token.expires_at?.slice(0, 10) || null,
      enabled: !token.enabled
    });
    message.success(result.message || (token.enabled ? 'Token 已停用' : 'Token 已启用'));
    await loadTokens();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '更新 Token 状态失败');
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

function confirmBatchDelete() {
  if (selectedTokenIds.value.length === 0) return;
  dialog.error({
    title: '批量删除 Token',
    content: `确认删除选中的 ${selectedTokenIds.value.length} 个 Token 吗？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: batchDeleteTokens
  });
}

async function batchDeleteTokens() {
  batchDeleting.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/tokens/batch-delete', { ids: selectedTokenIds.value });
    selectedTokenIds.value = [];
    message.success(result.message || 'Token 已删除');
    await loadTokens();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '批量删除 Token 失败');
  } finally {
    batchDeleting.value = false;
  }
}

async function copyToken(token: ApiTokenRecord) {
  if (!token.token) {
    message.warning('该 Token 是旧版本生成的，未保存完整值，请重生成后再复制');
    return;
  }
  await writeClipboardText(token.token);
  message.success('Token 已复制');
}

async function copyRawToken() {
  await writeClipboardText(rawToken.value);
  message.success('Token 已复制');
}

function tokenActionOptions(token: ApiTokenRecord): DropdownOption[] {
  return [
    { label: '编辑', key: 'edit' },
    { label: token.enabled ? '停用' : '启用', key: 'toggle' },
    { label: '重生成', key: 'regenerate' },
    { label: '删除', key: 'delete' }
  ];
}

function handleTokenAction(token: ApiTokenRecord, rawKey: string | number) {
  const key = String(rawKey);
  if (key === 'edit') {
    openEditDialog(token);
  } else if (key === 'toggle') {
    void toggleTokenEnabled(token);
  } else if (key === 'regenerate') {
    confirmRegenerate(token);
  } else if (key === 'delete') {
    confirmDelete(token);
  }
}

function isTokenSelected(tokenId: string): boolean {
  return selectedTokenIds.value.includes(tokenId);
}

function setTokenSelected(tokenId: string, checked: boolean | string | number) {
  if (Boolean(checked)) {
    if (!selectedTokenIds.value.includes(tokenId)) {
      selectedTokenIds.value.push(tokenId);
    }
    return;
  }
  selectedTokenIds.value = selectedTokenIds.value.filter(id => id !== tokenId);
}

function isTokenRevealed(tokenId: string): boolean {
  return visibleTokenIds.value.includes(tokenId);
}

function toggleTokenVisibility(token: ApiTokenRecord) {
  if (!token.token) {
    message.warning('该 Token 是旧版本生成的，未保存完整值，请重生成后再查看');
    return;
  }
  if (isTokenRevealed(token.id)) {
    visibleTokenIds.value = visibleTokenIds.value.filter(id => id !== token.id);
    return;
  }
  visibleTokenIds.value.push(token.id);
}

function tokenDisplayValue(token: ApiTokenRecord): string {
  if (token.token && isTokenRevealed(token.id)) {
    return token.token;
  }
  return `${token.prefix}...${token.suffix}`;
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

function defaultExpirationDate(): string {
  const date = new Date();
  date.setMonth(date.getMonth() + 1);
  return formatDateInput(date);
}

function formatDateInput(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
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

.api-token-select {
  flex: 0 0 auto;
  margin-top: 2px;
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

.api-token-value-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}

.api-token-value {
  min-width: 0;
  max-width: min(72ch, 100%);
  flex: 0 1 auto;
  overflow: hidden;
  color: var(--td-text-color-secondary);
  font-family: var(--td-font-family-mono);
  font-size: 12px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.api-token-value-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 2px;
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
  align-items: flex-start;
  gap: 6px;
}

.api-token-date-input {
  width: 100%;
  height: 34px;
  box-sizing: border-box;
  padding: 0 12px;
  border: 1px solid var(--td-border-color);
  border-radius: var(--td-radius-default);
  background: var(--td-card-bg);
  color: var(--td-text-color-primary);
  font: inherit;
  outline: none;
}

.api-token-date-input:focus {
  border-color: var(--n-primary-color, #18a058);
  box-shadow: 0 0 0 2px rgba(24, 160, 88, 0.12);
}

.api-token-date-input:disabled {
  cursor: not-allowed;
  opacity: 0.6;
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

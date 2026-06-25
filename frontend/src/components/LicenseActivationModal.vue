<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    title="授权延期"
    :mask-closable="!activationLoading"
    :style="{ width: '420px', maxWidth: 'calc(100vw - 32px)' }"
  >
    <div class="license-dialog-body">
      <p class="license-dialog-text">{{ licenseMessage }}</p>
      <div class="license-key-label">key: {{ activationKeyLabel }}</div>
      <n-input
        v-model:value="activationCode"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 5 }"
        placeholder="请输入激活码"
        :disabled="activationLoading"
      />
      <div class="license-metrix-toggle">
        <n-switch v-model:value="metrixEnabled" :loading="savingMetrix" size="small" @update:value="toggleMetrix" />
        <span class="license-metrix-label">启用 Metrix 平台</span>
      </div>
    </div>
    <template #footer>
      <div class="license-dialog-footer">
        <n-button :disabled="activationLoading" @click="visible = false">取消</n-button>
        <n-button type="primary" :loading="activationLoading" @click="submitActivation">激活</n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useMessage } from 'naive-ui';

import { apiGet, apiPost } from '../api/client';
import type { AppConfig, LicenseStatus } from '../types';

const visible = defineModel<boolean>('show', { required: true });
const emit = defineEmits<{ metrixChanged: [enabled: boolean] }>();
const message = useMessage();
const activationCode = ref('');
const activationLoading = ref(false);
const activationKeyLabel = ref('2026/12/30');
const licenseMessage = ref('输入激活码可将授权到期日期延长 30 天。');
const metrixEnabled = ref(false);
const savingMetrix = ref(false);

onMounted(() => {
  void loadLicenseStatus();
  void loadMetrixEnabled();
});

async function loadLicenseStatus() {
  try {
    const status = await apiGet<LicenseStatus>('/api/license/status');
    activationKeyLabel.value = status.key_label;
    licenseMessage.value = `当前授权到期日期：${status.expires_on}。输入激活码可延长 30 天。`;
    activationCode.value = '';
  } catch (error) {
    message.error(error instanceof Error ? error.message : '获取授权状态失败');
  }
}

async function loadMetrixEnabled() {
  try {
    const config = await apiGet<AppConfig>('/api/config/full');
    metrixEnabled.value = config.metrix_enabled ?? false;
  } catch {
    metrixEnabled.value = false;
  }
}

async function toggleMetrix(enabled: boolean) {
  savingMetrix.value = true;
  try {
    await apiPost('/api/config/metrix-enabled', { enabled });
    metrixEnabled.value = enabled;
    emit('metrixChanged', enabled);
  } catch (error) {
    metrixEnabled.value = !enabled;
    message.error(error instanceof Error ? error.message : '保存失败');
  } finally {
    savingMetrix.value = false;
  }
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
    licenseMessage.value = `当前授权到期日期：${result.expires_on}。输入激活码可继续延长 30 天。`;
    activationCode.value = '';
    message.success(`激活成功，到期日期: ${result.expires_on}`);
  } catch (error) {
    message.error(error instanceof Error ? error.message : '激活失败');
  } finally {
    activationLoading.value = false;
  }
}
</script>

<style scoped>
.license-metrix-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--n-border-color, #e0e0e6);
}
.license-metrix-label {
  font-size: 13px;
  color: var(--n-text-color-3, #999);
}
</style>

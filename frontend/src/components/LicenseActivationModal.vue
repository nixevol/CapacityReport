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
import type { LicenseStatus } from '../types';

const visible = defineModel<boolean>('show', { required: true });
const message = useMessage();
const activationCode = ref('');
const activationLoading = ref(false);
const activationKeyLabel = ref('2026/12/30');
const licenseMessage = ref('输入激活码可将授权到期日期延长 30 天。');

onMounted(() => {
  void loadLicenseStatus();
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

<template>
  <div class="login-page">
    <n-card class="login-card" :bordered="false">
      <div class="login-brand">
        <div class="brand-mark large">CR</div>
        <div>
          <h1>CapacityReport</h1>
          <p>容量报表处理系统</p>
        </div>
      </div>

      <n-form ref="formRef" :model="form" :rules="rules" @submit.prevent="submit">
        <n-form-item label="账号" path="username">
          <n-input v-model:value="form.username" autofocus />
        </n-form-item>
        <n-form-item label="密码" path="password">
          <n-input v-model:value="form.password" type="password" show-password-on="click" />
        </n-form-item>
        <n-button type="primary" block :loading="loading" @click="submit">登录</n-button>
      </n-form>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import type { FormInst, FormRules } from 'naive-ui';

defineProps<{ loading: boolean }>();
const emit = defineEmits<{ login: [{ username: string; password: string }] }>();

const formRef = ref<FormInst | null>(null);
const form = reactive({ username: 'root', password: '' });
const rules: FormRules = {
  username: { required: true, message: '请输入账号', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' }
};

async function submit() {
  await formRef.value?.validate();
  emit('login', { ...form });
}
</script>

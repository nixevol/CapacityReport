<template>
  <n-config-provider :theme="naiveTheme">
    <n-message-provider>
      <n-dialog-provider>
        <AppShell />
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { darkTheme } from 'naive-ui';

import AppShell from './AppShell.vue';
import { themeName } from './composables/theme';

const naiveTheme = computed(() => (themeName.value === 'dark' ? darkTheme : undefined));
</script>

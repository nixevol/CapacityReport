<template>
  <div class="api-docs-workspace">
    <n-card size="small" class="work-card api-docs-card">
      <template #header>
        <div class="api-docs-header">
          <div>
            <span class="api-docs-title">API 文档</span>
            <p class="api-docs-hint">Token 在系统设置的 API Token 分页生成，通过 Authorization: Bearer &lt;token&gt; 传递，也兼容 X-API-Token。</p>
          </div>
          <n-space size="small">
            <n-button size="small" tertiary @click="copyHeaderSample">复制传参示例</n-button>
            <n-button size="small" tertiary tag="a" :href="openApiUrl" target="_blank">OpenAPI JSON</n-button>
          </n-space>
        </div>
      </template>

      <div ref="swaggerHost" class="swagger-host" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue';
import { useMessage } from 'naive-ui';
import SwaggerUIBundle from 'swagger-ui-dist/swagger-ui-bundle.js';
import 'swagger-ui-dist/swagger-ui.css';

import { apiUrl, getApiBaseUrl, getToken } from '../api/client';

type SwaggerSystem = {
  getSystem?: () => {
    authActions?: {
      authorize?: (payload: Record<string, { name: string; schema: unknown; value: string }>) => void;
    };
  };
};

interface SwaggerRequest {
  headers: Record<string, string>;
  url?: string;
}

const message = useMessage();
const swaggerHost = ref<HTMLDivElement | null>(null);
const openApiUrl = apiUrl('/api/openapi.json');
let swaggerUi: SwaggerSystem | undefined;

onMounted(async () => {
  await nextTick();
  initSwagger();
});

function initSwagger() {
  if (!swaggerHost.value) return;

  swaggerHost.value.innerHTML = '';
  swaggerUi = SwaggerUIBundle({
    url: openApiUrl,
    domNode: swaggerHost.value,
    requestSnippetsEnabled: true,
    deepLinking: true,
    docExpansion: 'list',
    defaultModelsExpandDepth: -1,
    displayRequestDuration: true,
    persistAuthorization: true,
    filter: true,
    validatorUrl: null,
    showCommonExtensions: true,
    showExtensions: false,
    requestInterceptor: (request: SwaggerRequest) => {
      const token = getToken();
      if (token && !request.headers.Authorization && !request.headers.authorization) {
        request.headers.Authorization = `Bearer ${token}`;
      }
      if (request.url?.startsWith('/')) {
        request.url = `${getApiBaseUrl()}${request.url}`;
      }
      return request;
    },
    onComplete: () => {
      const token = getToken();
      if (!token) return;
      swaggerUi?.getSystem?.().authActions?.authorize?.({
        BearerAuth: {
          name: 'BearerAuth',
          schema: { type: 'http', scheme: 'bearer' },
          value: token
        }
      });
    }
  }) as SwaggerSystem;
}

async function copyHeaderSample() {
  await writeClipboard('Authorization: Bearer <token>\nX-API-Token: <token>');
  message.success('传参示例已复制');
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
</script>

<style scoped>
.api-docs-workspace {
  display: flex;
  height: 100%;
  min-height: 0;
  min-width: 0;
  padding: 24px 32px;
}

.api-docs-card {
  display: flex;
  width: 100%;
  min-height: 0;
  flex-direction: column;
}

.api-docs-card > :deep(.n-card__content),
.api-docs-card > :deep(.n-card-content) {
  flex: 1;
  min-height: 0;
}

.api-docs-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.api-docs-title {
  color: var(--td-text-color-primary);
  font-size: 15px;
  font-weight: 600;
}

.api-docs-hint {
  margin: 4px 0 0;
  color: var(--td-text-color-secondary);
  font-size: 12px;
}

.swagger-host {
  height: 100%;
  min-height: 0;
  overflow: auto;
  border: 1px solid var(--td-border-color-light);
  border-radius: var(--td-radius-default);
  background: #fff;
}

:deep(.swagger-ui) {
  color: #1f2937;
}

:deep(.swagger-ui .scheme-container) {
  box-shadow: none;
}

:deep(.swagger-ui .models),
:deep(.swagger-ui section.models) {
  display: none !important;
}

@media (max-width: 900px) {
  .api-docs-workspace {
    height: auto;
    padding: 16px;
  }

  .swagger-host {
    min-height: 70vh;
  }
}
</style>

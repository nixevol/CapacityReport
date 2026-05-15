<template>
  <div class="script-workspace">
    <n-card size="small" class="work-card script-editor-pane">
      <template #header>
        <div class="script-card-title">
          <span>脚本编辑</span>
          <n-tag v-if="isModified" size="small" type="warning">已修改</n-tag>
          <n-tag v-else size="small" type="success">已保存</n-tag>
        </div>
      </template>
      <template #header-extra>
        <n-space>
          <n-button size="small" tertiary :loading="loading" @click="loadScript">重新加载</n-button>
          <n-button size="small" type="primary" :loading="saving" @click="saveScript">保存</n-button>
          <n-button size="small" type="warning" :loading="executing" @click="executeScript">执行</n-button>
        </n-space>
      </template>

      <div class="script-editor-toolbar">
        <span class="script-path" :title="scriptPath">{{ scriptPath || 'ReportScript.sql' }}</span>
        <span class="script-modified">修改时间：{{ modified || '-' }}</span>
      </div>

      <div ref="editorHost" class="monaco-editor-host" />

      <div class="script-status-bar">
        <span>{{ cursorText }}</span>
        <span>{{ lineCount }} 行</span>
        <span>{{ editorStatus }}</span>
      </div>
    </n-card>

    <n-card title="执行状态" size="small" class="work-card script-log-pane">
      <template #header-extra>
        <n-space>
          <n-tag v-if="taskStatus" :type="statusType">{{ statusText }}</n-tag>
          <n-button size="small" tertiary :disabled="!taskId" @click="refreshStatus">刷新</n-button>
        </n-space>
      </template>

      <n-empty v-if="!taskStatus" description="脚本尚未执行" />
      <n-log v-else :log="logText" language="text" trim class="script-log" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue';
import { useMessage } from 'naive-ui';
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api.js';
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import 'monaco-editor/esm/vs/basic-languages/sql/sql.contribution';

import { apiGet, apiPost } from '../api/client';
import type { ApiMessage, ScriptContent, TaskStatus } from '../types';

type MonacoGlobal = typeof globalThis & {
  MonacoEnvironment?: {
    getWorker: (_moduleId: string, _label: string) => Worker;
  };
};

(globalThis as MonacoGlobal).MonacoEnvironment = {
  getWorker: () => new editorWorker()
};

const message = useMessage();
const editorHost = ref<HTMLDivElement | null>(null);
const editor = shallowRef<monaco.editor.IStandaloneCodeEditor | null>(null);
const disposables: monaco.IDisposable[] = [];
const content = ref('');
const originalContent = ref('');
const scriptPath = ref('');
const modified = ref<string | null>(null);
const cursorText = ref('行 1，列 1');
const lineCount = ref(1);
const isModified = ref(false);
const loading = ref(false);
const saving = ref(false);
const executing = ref(false);
const taskId = ref('');
const taskStatus = ref<TaskStatus | null>(null);
let timer: number | undefined;
let applyingRemoteContent = false;

const logText = computed(() => taskStatus.value?.logs?.join('\n') || '等待执行日志');
const statusType = computed(() => {
  if (taskStatus.value?.status === 'completed') return 'success';
  if (taskStatus.value?.status === 'failed') return 'error';
  return 'info';
});
const statusText = computed(() => {
  const status = taskStatus.value?.status;
  if (status === 'completed') return '已完成';
  if (status === 'failed') return '失败';
  if (status === 'processing') return '执行中';
  if (status === 'pending') return '等待中';
  return status || '';
});
const editorStatus = computed(() => {
  if (loading.value) return '加载中';
  if (saving.value) return '保存中';
  return isModified.value ? '未保存' : '就绪';
});

onMounted(async () => {
  await nextTick();
  createEditor();
  await loadScript();
});

onBeforeUnmount(() => {
  stopPolling();
  for (const disposable of disposables) {
    disposable.dispose();
  }
  editor.value?.dispose();
});

function createEditor() {
  if (!editorHost.value || editor.value) return;

  editor.value = monaco.editor.create(editorHost.value, {
    value: '-- 正在加载 ReportScript.sql',
    language: 'sql',
    theme: 'vs',
    fontSize: 14,
    fontFamily: "'Cascadia Code', Consolas, 'Courier New', monospace",
    lineNumbers: 'on',
    minimap: { enabled: true },
    automaticLayout: true,
    scrollBeyondLastLine: false,
    roundedSelection: false,
    renderLineHighlight: 'all',
    tabSize: 4,
    wordWrap: 'off'
  });

  disposables.push(
    editor.value.onDidChangeCursorPosition(updateCursor),
    editor.value.onDidChangeModelContent(() => {
      const value = getEditorContent();
      content.value = value;
      lineCount.value = editor.value?.getModel()?.getLineCount() || 1;
      if (!applyingRemoteContent) {
        isModified.value = value !== originalContent.value;
      }
    })
  );

  editor.value.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
    void saveScript();
  });

  updateCursor();
}

async function loadScript() {
  loading.value = true;
  try {
    const result = await apiGet<ScriptContent>('/api/script/content');
    if (!result.success) {
      throw new Error(result.error || '加载脚本失败');
    }
    applyScriptContent(result.content);
    scriptPath.value = result.path;
    modified.value = result.modified;
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载脚本失败');
  } finally {
    loading.value = false;
  }
}

async function saveScript() {
  saving.value = true;
  try {
    const value = getEditorContent();
    const result = await apiPost<ApiMessage & { modified?: string }>('/api/script/save', {
      content: value
    });
    if (!result.success) {
      throw new Error(result.error || '保存失败');
    }
    originalContent.value = value;
    isModified.value = false;
    modified.value = result.modified || modified.value;
    message.success(result.message || '保存成功');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存脚本失败');
  } finally {
    saving.value = false;
  }
}

async function executeScript() {
  executing.value = true;
  try {
    if (isModified.value) {
      await saveScript();
      if (isModified.value) return;
    }

    const result = await apiPost<ApiMessage>('/api/script/execute');
    if (!result.task_id) {
      throw new Error(result.message || '脚本任务启动失败');
    }
    taskId.value = result.task_id;
    taskStatus.value = { task_id: result.task_id, status: 'processing', logs: [] };
    message.success(result.message || '脚本任务已启动');
    startPolling();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '执行脚本失败');
  } finally {
    executing.value = false;
  }
}

function applyScriptContent(value: string) {
  applyingRemoteContent = true;
  content.value = value;
  originalContent.value = value;
  if (editor.value && editor.value.getValue() !== value) {
    editor.value.setValue(value);
  }
  lineCount.value = editor.value?.getModel()?.getLineCount() || value.split(/\r\n|\r|\n/).length || 1;
  isModified.value = false;
  applyingRemoteContent = false;
  updateCursor();
}

function getEditorContent() {
  return editor.value?.getValue() ?? content.value;
}

function updateCursor() {
  const position = editor.value?.getPosition();
  cursorText.value = position ? `行 ${position.lineNumber}，列 ${position.column}` : '行 1，列 1';
}

function startPolling() {
  stopPolling();
  void refreshStatus();
  timer = window.setInterval(() => void refreshStatus(), 1500);
}

function stopPolling() {
  if (timer) {
    window.clearInterval(timer);
    timer = undefined;
  }
}

async function refreshStatus() {
  if (!taskId.value) return;
  try {
    taskStatus.value = await apiPost<TaskStatus>('/api/process/status', { task_id: taskId.value });
    if (['completed', 'failed'].includes(taskStatus.value.status)) {
      stopPolling();
    }
  } catch (error) {
    stopPolling();
    message.error(error instanceof Error ? error.message : '刷新执行状态失败');
  }
}
</script>

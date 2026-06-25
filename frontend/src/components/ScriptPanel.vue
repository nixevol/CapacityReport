<template>
  <div class="script-page-body">
    <div class="script-editor-container">
      <div ref="editorHost" class="script-editor" />
    </div>

    <div v-if="taskStatus || taskId" class="script-process-section">
      <div class="upload-process-card script-process-card">
        <div class="card-header">
          <div class="card-header-left">
            <span class="card-title">脚本执行进度</span>
            <span class="process-status" :class="statusClass">{{ statusText }}</span>
          </div>
          <div class="card-header-right">
            <n-button size="small" tertiary :disabled="!taskId" @click="refreshStatus">刷新</n-button>
          </div>
        </div>
        <div class="card-body">
          <div class="colored-log-panel script-log" role="log" aria-label="脚本执行日志">
            <pre class="colored-log-content"><span
              v-for="(line, index) in logLines"
              :key="index"
              class="colored-log-line"
              :class="`log-level-${line.level}`"
            >{{ line.text }}</span></pre>
          </div>
        </div>
      </div>
    </div>

    <div class="script-status-bar">
      <span>{{ cursorText }}</span>
      <span>{{ editorStatus }}</span>
      <span>{{ lineCount }} 行</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue';
import { useMessage } from 'naive-ui';
import {
  BrushOutline,
  PlayOutline,
  SaveOutline,
  SwapHorizontalOutline,
} from '@vicons/ionicons5';
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api.js';
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import 'monaco-editor/esm/vs/basic-languages/sql/sql.contribution';

import { apiGet, apiPost } from '../api/client';
import type { ApiMessage, ScriptContent, TaskStatus } from '../types';
import { toColoredLogLines } from '../composables/logLines';
import { resetPageHeader, setPageHeader } from '../composables/pageHeader';

type MonacoGlobal = typeof globalThis & {
  MonacoEnvironment?: {
    getWorker: (_moduleId: string, _label: string) => Worker;
  };
  __capacityReportScriptTaskState?: {
    taskId: ReturnType<typeof ref<string>>;
    taskStatus: ReturnType<typeof ref<TaskStatus | null>>;
  };
};

(globalThis as MonacoGlobal).MonacoEnvironment = {
  getWorker: () => new editorWorker()
};

const SCRIPT_OPTIONS = [
  { key: 'report', label: '容量报表脚本' },
  { key: 'celldata', label: 'CellData 脚本' },
];

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
const scriptType = ref('report');
let timer: number | undefined;
let themeObserver: MutationObserver | undefined;
let applyingRemoteContent = false;

const globalWindow = window as MonacoGlobal;
const scriptTaskState = globalWindow.__capacityReportScriptTaskState || {
  taskId: ref(''),
  taskStatus: ref<TaskStatus | null>(null)
};
globalWindow.__capacityReportScriptTaskState = scriptTaskState;
const taskId = scriptTaskState.taskId;
const taskStatus = scriptTaskState.taskStatus;

const logText = computed(() => taskStatus.value?.logs?.join('\n') || '等待执行日志');
const logLines = computed(() => toColoredLogLines(logText.value, '等待执行日志'));
const statusClass = computed(() => {
  if (taskStatus.value?.status === 'completed') return 'completed';
  if (taskStatus.value?.status === 'failed') return 'failed';
  return 'processing';
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
const modifiedText = computed(() => (modified.value ? `最后修改: ${modified.value}` : '最后修改: -'));
const currentLabel = computed(() => SCRIPT_OPTIONS.find(o => o.key === scriptType.value)?.label || scriptType.value);

onMounted(async () => {
  setPageHeader({
    subtitle: computed(() => scriptPath.value || currentLabel.value),
    actions: [
      { key: 'script-modified', kind: 'text', label: modifiedText },
      {
        key: 'switch-script',
        label: computed(() => currentLabel.value),
        icon: SwapHorizontalOutline,
        dropdownOptions: SCRIPT_OPTIONS,
        onSelect: (key) => void switchScript(String(key)),
      },
      {
        key: 'save-script',
        label: computed(() => (isModified.value ? '保存 *' : '保存')),
        icon: SaveOutline,
        type: 'primary',
        variant: 'solid',
        loading: saving,
        onClick: saveScript
      },
      { key: 'format-script', label: '格式化', icon: BrushOutline, onClick: formatScript },
      {
        key: 'run-script',
        label: '运行',
        icon: PlayOutline,
        type: 'success',
        variant: 'solid',
        loading: executing,
        onClick: executeScript
      }
    ]
  });

  await nextTick();
  createEditor();
  observeTheme();
  await loadScript();
  if (taskId.value && taskStatus.value && !['completed', 'failed'].includes(taskStatus.value.status)) {
    startPolling();
  }
});

onBeforeUnmount(() => {
  resetPageHeader();
  stopPolling();
  themeObserver?.disconnect();
  for (const disposable of disposables) {
    disposable.dispose();
  }
  editor.value?.dispose();
});

function createEditor() {
  if (!editorHost.value || editor.value) return;

  editor.value = monaco.editor.create(editorHost.value, {
    value: '-- 正在加载脚本...',
    language: 'sql',
    theme: currentEditorTheme(),
    fontSize: 14,
    fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, 'Courier New', monospace",
    lineNumbers: 'on',
    minimap: { enabled: true },
    automaticLayout: true,
    scrollBeyondLastLine: false,
    roundedSelection: true,
    renderLineHighlight: 'all',
    tabSize: 4,
    insertSpaces: true,
    wordWrap: 'on',
    folding: true,
    showFoldingControls: 'always',
    bracketPairColorization: { enabled: true },
    guides: {
      bracketPairs: true,
      indentation: true
    }
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

async function switchScript(type: string) {
  if (type === scriptType.value) return;
  if (isModified.value) {
    const confirm = window.confirm(`当前脚本有未保存的修改，是否放弃？`);
    if (!confirm) return;
  }
  await loadScript(type);
}

async function loadScript(type?: string) {
  const target = type || scriptType.value;
  loading.value = true;
  try {
    const result = await apiGet<ScriptContent & { script_type?: string }>(`/api/script/content?script_type=${target}`);
    if (!result.success) {
      throw new Error(result.error || '加载脚本失败');
    }
    scriptType.value = target;
    scriptPath.value = result.path || '';
    modified.value = result.modified;
    applyScriptContent(result.content);
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
      content: value,
      script_type: scriptType.value
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

async function formatScript() {
  const action = editor.value?.getAction('editor.action.formatDocument');
  if (!action) {
    message.warning('当前编辑器没有可用的格式化动作');
    return;
  }

  await action.run();
  message.success('格式化完成');
}

async function executeScript() {
  executing.value = true;
  try {
    if (isModified.value) {
      await saveScript();
      if (isModified.value) return;
    }

    const result = await apiPost<ApiMessage>('/api/script/execute', {
      script_type: scriptType.value
    });
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
  editor.value?.setValue(value);
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

function observeTheme() {
  themeObserver = new MutationObserver(() => {
    monaco.editor.setTheme(currentEditorTheme());
  });
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
}

function currentEditorTheme() {
  return document.documentElement.getAttribute('data-theme') === 'dark' ? 'vs-dark' : 'vs';
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

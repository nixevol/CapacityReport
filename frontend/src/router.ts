import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

const FileWorkflow = () => import('./components/FileWorkflow.vue');
const HistoryPanel = () => import('./components/HistoryPanel.vue');
const DatabasePanel = () => import('./components/DatabasePanel.vue');
const SettingsPanel = () => import('./components/SettingsPanel.vue');
const ScriptPanel = () => import('./components/ScriptPanel.vue');
const ApiDocs = () => import('./components/ApiDocs.vue');

export const routes: RouteRecordRaw[] = [
  { path: '/', redirect: { name: 'workflow' } },
  { path: '/upload', name: 'workflow', component: FileWorkflow, meta: { title: '数据处理' } },
  { path: '/history', name: 'history', component: HistoryPanel, meta: { title: '处理历史' } },
  { path: '/database', name: 'database', component: DatabasePanel, meta: { title: '数据管理' } },
  { path: '/script', name: 'script', component: ScriptPanel, meta: { title: '脚本编辑' } },
  { path: '/api-docs', alias: '/api-center', name: 'api-center', component: ApiDocs, meta: { title: 'API 文档' } },
  { path: '/settings', name: 'settings', component: SettingsPanel, meta: { title: '系统设置' } },
  { path: '/:pathMatch(.*)*', redirect: { name: 'workflow' } }
];

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
});

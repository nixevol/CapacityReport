import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

import FileWorkflow from './components/FileWorkflow.vue';
import HistoryPanel from './components/HistoryPanel.vue';
import DatabasePanel from './components/DatabasePanel.vue';
import SettingsPanel from './components/SettingsPanel.vue';

const ScriptPanel = () => import('./components/ScriptPanel.vue');

export const routes: RouteRecordRaw[] = [
  { path: '/', redirect: { name: 'workflow' } },
  { path: '/upload', name: 'workflow', component: FileWorkflow, meta: { title: '数据上传' } },
  { path: '/history', name: 'history', component: HistoryPanel, meta: { title: '处理历史' } },
  { path: '/database', name: 'database', component: DatabasePanel, meta: { title: '数据管理' } },
  { path: '/script', name: 'script', component: ScriptPanel, meta: { title: '脚本编辑' } },
  { path: '/settings', name: 'settings', component: SettingsPanel, meta: { title: '系统设置' } },
  { path: '/:pathMatch(.*)*', redirect: { name: 'workflow' } }
];

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
});

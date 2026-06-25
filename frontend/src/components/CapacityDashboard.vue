<template>
  <div class="cap-dashboard">
    <!-- 加载中 -->
    <div v-if="loadingStatus" class="cap-center">
      <n-spin size="large" />
    </div>

    <!-- 无结果表：居中提示 -->
    <div v-else-if="!ready" class="cap-center cap-empty">
      <div class="cap-empty-orb"></div>
      <p class="cap-empty-text">请先进行数据处理</p>
      <p class="cap-empty-sub">检测到数据库中暂无 4G / 5G 结果表，完成「数据处理」后即可查看容量看板。</p>
    </div>

    <!-- 看板主体 -->
    <div v-else class="cap-body">
      <header class="cap-topbar">
        <div class="cap-title-wrap">
          <span class="cap-spark"></span>
          <h2 class="cap-title">容量负荷看板</h2>
          <span class="cap-sub">高负荷小区分析 · 实时数据</span>
        </div>
        <div class="cap-controls">
          <div class="cap-seg">
            <button
              v-for="opt in ratOptions"
              :key="opt.value"
              type="button"
              class="cap-seg-btn"
              :class="{ active: rat === opt.value }"
              @click="switchRat(opt.value)"
            >{{ opt.label }}</button>
          </div>
          <button class="cap-refresh" type="button" :disabled="loadingOverview" title="刷新" @click="reload">
            <n-icon><RefreshOutline /></n-icon>
          </button>
        </div>
      </header>

      <n-spin :show="loadingOverview">
        <!-- 汇总卡片 -->
        <section class="cap-cards">
          <div
            v-for="(card, idx) in cards"
            :key="card.key"
            class="cap-card"
            :class="card.tone"
            :style="{ animationDelay: idx * 60 + 'ms' }"
          >
            <div class="cap-card-icon"><n-icon><component :is="card.icon" /></n-icon></div>
            <div class="cap-card-body">
              <div class="cap-card-value">{{ card.display }}<span v-if="card.unit" class="cap-card-unit">{{ card.unit }}</span></div>
              <div class="cap-card-label">{{ card.label }}</div>
            </div>
            <div class="cap-card-glow"></div>
          </div>
        </section>

        <!-- 图表区 -->
        <section class="cap-charts">
          <div class="cap-panel span-2">
            <div class="cap-panel-head"><span class="bar"></span>负荷问题分布</div>
            <e-chart :option="problemOption" height="280px" />
          </div>
          <div class="cap-panel span-4">
            <div class="cap-panel-head"><span class="bar"></span>下行利用率分布（{{ overview?.labels.dl }}）</div>
            <e-chart :option="histOption" height="280px" />
          </div>
          <div class="cap-panel span-3">
            <div class="cap-panel-head"><span class="bar"></span>制式分布（总数 / 高负荷）</div>
            <e-chart :option="systemOption" height="260px" />
          </div>
          <div class="cap-panel span-3">
            <div class="cap-panel-head"><span class="bar"></span>带宽分布（总数 / 高负荷）</div>
            <e-chart :option="bandOption" height="260px" />
          </div>
          <div class="cap-panel span-2">
            <div class="cap-panel-head"><span class="bar"></span>站型分布</div>
            <e-chart :option="stationOption" height="260px" />
          </div>
          <div class="cap-panel span-4">
            <div class="cap-panel-head"><span class="bar"></span>频段标记小区 Top</div>
            <e-chart :option="freqOption" height="260px" />
          </div>
        </section>

        <!-- 高负荷 / 预警 清单 -->
        <section class="cap-panel cap-list">
          <div class="cap-list-head">
            <div class="cap-panel-head"><span class="bar"></span>问题小区清单</div>
            <div class="cap-list-filters">
              <div class="cap-seg sm">
                <button
                  v-for="opt in problemFilters"
                  :key="opt.value"
                  type="button"
                  class="cap-seg-btn"
                  :class="{ active: problemFilter === opt.value }"
                  @click="setProblemFilter(opt.value)"
                >{{ opt.label }}</button>
              </div>
              <n-input
                v-model:value="keyword"
                class="cap-search"
                clearable
                placeholder="CGI / 小区名称"
                @keyup.enter="searchCells"
                @clear="searchCells"
              >
                <template #prefix><n-icon><SearchOutline /></n-icon></template>
              </n-input>
              <n-button size="small" type="primary" ghost @click="searchCells">查询</n-button>
            </div>
          </div>
          <n-data-table
            class="cap-table"
            :columns="columns"
            :data="cells"
            :loading="loadingCells"
            :bordered="false"
            :scroll-x="1180"
            :row-props="rowProps"
          />
          <div class="cap-pager">
            <span class="cap-pager-total">共 {{ cellTotal }} 个问题小区</span>
            <n-pagination
              :page="page"
              :page-count="pageCount"
              :page-size="pageSize"
              @update:page="changePage"
            />
          </div>
        </section>
      </n-spin>
    </div>

    <!-- 小区详情抽屉 -->
    <n-drawer v-model:show="detailVisible" :width="detailWidth" placement="right" class="cap-drawer">
      <n-drawer-content :native-scrollbar="false" closable>
        <template #header>
          <div class="cap-detail-head">
            <span class="cap-detail-id">{{ detail?.id }}</span>
            <span v-if="detail?.name" class="cap-detail-name">{{ detail?.name }}</span>
          </div>
        </template>
        <div v-if="loadingDetail" class="cap-center"><n-spin /></div>
        <div v-else-if="detail" class="cap-detail">
          <div class="cap-detail-tags">
            <span class="cap-tag" :class="problemClass(detailProblem)">{{ detailProblem || '正常' }}</span>
            <span class="cap-tag plain">{{ detailValue('制式') }}</span>
            <span class="cap-tag plain">{{ detailValue('带宽') }}</span>
            <span class="cap-tag plain">{{ detailValue('站型') }}</span>
            <span class="cap-tag plain">{{ detailValue('频段') }}</span>
          </div>

          <div class="cap-detail-grid">
            <div v-for="m in detailMetrics" :key="m.label" class="cap-metric">
              <div class="cap-metric-label">{{ m.label }}</div>
              <div class="cap-metric-value">{{ m.value }}</div>
            </div>
          </div>

          <div v-if="detailSuggestion" class="cap-suggest">
            <div class="cap-suggest-head"><n-icon><BulbOutline /></n-icon> 优化建议</div>
            <p class="cap-suggest-text">{{ detailSuggestion }}</p>
          </div>

          <div class="cap-sib">
            <div class="cap-panel-head sm"><span class="bar"></span>同扇区同运营商小区（{{ detail.siblings.length }}）</div>
            <n-empty v-if="!detail.siblings.length" size="small" description="无同扇区其他小区" />
            <div v-else class="cap-sib-list">
              <div v-for="sib in detail.siblings" :key="sib.id" class="cap-sib-item">
                <div class="cap-sib-main">
                  <span class="cap-sib-id">{{ sib.id }}</span>
                  <span class="cap-sib-name">{{ sib.name }}</span>
                </div>
                <div class="cap-sib-meta">
                  <span class="cap-tag plain xs">{{ sib.band || '-' }}</span>
                  <span class="cap-tag plain xs">{{ sib.freq || '-' }}</span>
                  <span class="cap-sib-stat">下行 {{ sib.dl }}%</span>
                  <span class="cap-sib-stat">流量 {{ sib.flow }}GB</span>
                  <span class="cap-tag xs" :class="problemClass(sib.problem)">{{ sib.problem }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, type Component } from 'vue';
import { NTag, useMessage } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import type { EChartsOption } from 'echarts';
import {
  AlertCircleOutline,
  AnalyticsOutline,
  BulbOutline,
  CellularOutline,
  FlashOutline,
  PulseOutline,
  RefreshOutline,
  SearchOutline,
  TrendingUpOutline
} from '@vicons/ionicons5';

import { apiGet } from '../api/client';
import EChart from './EChart.vue';

type Rat = '4g' | '5g';
interface NameVal { name: string; value: number }
interface CatStat { name: string; total: number; high: number; flagged: number }
interface HistBucket { bucket: string; value: number }
interface TopCell { id: string; name: string; system: string; band: string; station: string; ul: number; dl: number; flow: number; users: number; problem: string }
interface Overview {
  rat: string;
  labels: { ul: string; dl: string };
  summary: { total: number; high_load: number; util_warn: number; flow_warn: number; normal: number; avg_dl: number; max_dl: number; avg_flow: number; total_flow: number };
  problem_pie: NameVal[];
  by_system: CatStat[];
  by_band: CatStat[];
  by_station: CatStat[];
  by_freq: CatStat[];
  util_hist: HistBucket[];
  top_cells: TopCell[];
}
interface CellRow { id: string; name: string; system: string; band: string; station: string; freq: string; ul: number; dl: number; flow: number; users: number; problem: string; is_high: string }
interface Sibling { id: string; name: string; band: string; freq: string; ul: number; dl: number; flow: number; problem: string }
interface CellDetail {
  rat: string; id: string; name: string; labels: { ul: string; dl: string };
  ul_field: string; dl_field: string; users_field: string; flow_field: string;
  detail: Record<string, unknown>; siblings: Sibling[];
}

const message = useMessage();

const loadingStatus = ref(true);
const ready = ref(false);
const rat = ref<Rat>('4g');
const ratOptions: { label: string; value: Rat }[] = [
  { label: '4G', value: '4g' },
  { label: '5G', value: '5g' }
];

const loadingOverview = ref(false);
const overview = ref<Overview | null>(null);

const cells = ref<CellRow[]>([]);
const cellTotal = ref(0);
const page = ref(1);
const pageSize = 20;
const loadingCells = ref(false);
const problemFilter = ref('');
const keyword = ref('');
const problemFilters = [
  { label: '全部', value: '' },
  { label: '高负荷', value: '高负荷' },
  { label: '高流量预警', value: '高流量预警' },
  { label: '利用率预警', value: '利用率预警' }
];

const detailVisible = ref(false);
const loadingDetail = ref(false);
const detail = ref<CellDetail | null>(null);
const detailWidth = ref(Math.min(560, typeof window !== 'undefined' ? window.innerWidth - 24 : 560));

const pageCount = computed(() => Math.max(1, Math.ceil(cellTotal.value / pageSize)));

const PALETTE = ['#38bdf8', '#22d3ee', '#818cf8', '#c084fc', '#fbbf24', '#fb7185', '#34d399', '#f472b6'];
const PROBLEM_COLOR: Record<string, string> = {
  高负荷: '#fb7185',
  高流量预警: '#fbbf24',
  利用率预警: '#38bdf8',
  正常: '#475569'
};

// ---------- 汇总卡片（含数字滚动） ----------
const animated = reactive<Record<string, number>>({ total: 0, high_load: 0, util_warn: 0, flow_warn: 0, avg_dl: 0, total_flow: 0 });

const cards = computed(() => {
  const s = overview.value?.summary;
  const defs: { key: keyof typeof animated; label: string; icon: Component; tone: string; unit?: string; digits?: number }[] = [
    { key: 'total', label: '小区总数', icon: CellularOutline, tone: 'tone-cyan' },
    { key: 'high_load', label: '高负荷小区', icon: FlashOutline, tone: 'tone-rose' },
    { key: 'util_warn', label: '利用率预警', icon: PulseOutline, tone: 'tone-blue' },
    { key: 'flow_warn', label: '高流量预警', icon: TrendingUpOutline, tone: 'tone-amber' },
    { key: 'avg_dl', label: '平均下行利用率', icon: AnalyticsOutline, tone: 'tone-violet', unit: '%', digits: 1 },
    { key: 'total_flow', label: '总日均流量', icon: AlertCircleOutline, tone: 'tone-emerald', unit: 'GB', digits: 0 }
  ];
  void s;
  return defs.map(d => ({
    ...d,
    display: formatNum(animated[d.key], d.digits ?? 0)
  }));
});

function formatNum(value: number, digits: number): string {
  const fixed = Number(value).toFixed(digits);
  const [int, dec] = fixed.split('.');
  const withSep = int.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return dec ? `${withSep}.${dec}` : withSep;
}

function animateCards(s: Overview['summary']) {
  const targets: Record<string, number> = {
    total: s.total, high_load: s.high_load, util_warn: s.util_warn,
    flow_warn: s.flow_warn, avg_dl: s.avg_dl, total_flow: s.total_flow
  };
  const start = performance.now();
  const from = { ...animated };
  const step = (now: number) => {
    const t = Math.min(1, (now - start) / 700);
    const ease = 1 - Math.pow(1 - t, 3);
    for (const k of Object.keys(targets)) {
      animated[k] = from[k] + (targets[k] - from[k]) * ease;
    }
    if (t < 1) requestAnimationFrame(step);
    else Object.assign(animated, targets);
  };
  requestAnimationFrame(step);
}

// ---------- echarts 通用主题 ----------
function baseGrid(): EChartsOption['grid'] {
  return { left: 8, right: 16, top: 28, bottom: 8, containLabel: true };
}
function axisLine() {
  return { lineStyle: { color: 'rgba(148,163,184,0.25)' } };
}
function axisLabel() {
  return { color: '#94a3b8', fontSize: 11 };
}
function tooltipBase(): EChartsOption['tooltip'] {
  return {
    backgroundColor: 'rgba(15,23,42,0.92)',
    borderColor: 'rgba(56,189,248,0.35)',
    borderWidth: 1,
    textStyle: { color: '#e2e8f0', fontSize: 12 }
  };
}

const problemOption = computed<EChartsOption>(() => {
  const data = (overview.value?.problem_pie || []).map(d => ({
    name: d.name, value: d.value,
    itemStyle: { color: PROBLEM_COLOR[d.name] || '#64748b' }
  }));
  return {
    tooltip: { ...tooltipBase(), trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { color: '#94a3b8', fontSize: 11 }, icon: 'circle' },
    series: [{
      type: 'pie', radius: ['46%', '72%'], center: ['50%', '44%'], avoidLabelOverlap: true,
      itemStyle: { borderColor: 'rgba(2,6,23,0.6)', borderWidth: 2 },
      label: { show: false }, labelLine: { show: false },
      data
    }]
  };
});

const histOption = computed<EChartsOption>(() => {
  const buckets = overview.value?.util_hist || [];
  return {
    tooltip: { ...tooltipBase(), trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: baseGrid(),
    xAxis: { type: 'category', data: buckets.map(b => b.bucket), axisLine: axisLine(), axisLabel: { ...axisLabel(), rotate: 30 }, axisTick: { show: false } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(148,163,184,0.12)' } }, axisLabel: axisLabel() },
    series: [{
      type: 'bar', barWidth: '58%', data: buckets.map(b => b.value),
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#22d3ee' }, { offset: 1, color: 'rgba(56,189,248,0.15)' }] }
      }
    }]
  };
});

function groupedBar(stats: CatStat[]): EChartsOption {
  return {
    tooltip: { ...tooltipBase(), trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, right: 0, textStyle: { color: '#94a3b8', fontSize: 11 }, itemWidth: 10, itemHeight: 10 },
    grid: baseGrid(),
    xAxis: { type: 'category', data: stats.map(s => s.name), axisLine: axisLine(), axisLabel: { ...axisLabel(), interval: 0, rotate: stats.length > 5 ? 24 : 0 }, axisTick: { show: false } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(148,163,184,0.12)' } }, axisLabel: axisLabel() },
    series: [
      { name: '总数', type: 'bar', barGap: '-100%', barWidth: '52%', itemStyle: { borderRadius: [3, 3, 0, 0], color: 'rgba(56,189,248,0.18)' }, data: stats.map(s => s.total) },
      { name: '高负荷', type: 'bar', barWidth: '52%', itemStyle: { borderRadius: [3, 3, 0, 0], color: '#fb7185' }, data: stats.map(s => s.high) }
    ]
  };
}
const systemOption = computed<EChartsOption>(() => groupedBar(overview.value?.by_system || []));
const bandOption = computed<EChartsOption>(() => groupedBar(overview.value?.by_band || []));

const stationOption = computed<EChartsOption>(() => {
  const data = (overview.value?.by_station || []).map((s, i) => ({ name: s.name, value: s.total, itemStyle: { color: PALETTE[i % PALETTE.length] } }));
  return {
    tooltip: { ...tooltipBase(), trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { color: '#94a3b8', fontSize: 11 }, icon: 'circle' },
    series: [{
      type: 'pie', radius: ['42%', '70%'], center: ['50%', '44%'],
      itemStyle: { borderColor: 'rgba(2,6,23,0.6)', borderWidth: 2 },
      label: { show: false }, labelLine: { show: false }, data
    }]
  };
});

const freqOption = computed<EChartsOption>(() => {
  const stats = [...(overview.value?.by_freq || [])].sort((a, b) => a.flagged - b.flagged);
  return {
    tooltip: { ...tooltipBase(), trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 8, right: 24, top: 12, bottom: 8, containLabel: true },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(148,163,184,0.12)' } }, axisLabel: axisLabel() },
    yAxis: { type: 'category', data: stats.map(s => s.name), axisLine: axisLine(), axisLabel: axisLabel(), axisTick: { show: false } },
    series: [{
      type: 'bar', barWidth: '56%', data: stats.map(s => s.flagged),
      itemStyle: {
        borderRadius: [0, 4, 4, 0],
        color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: 'rgba(129,140,248,0.2)' }, { offset: 1, color: '#818cf8' }] }
      }
    }]
  };
});

// ---------- 清单表格 ----------
const columns = computed<DataTableColumns<CellRow>>(() => [
  { title: overview.value?.rat === '5g' ? 'NCGI' : 'CGI', key: 'id', width: 180, ellipsis: { tooltip: true }, fixed: 'left' },
  { title: '小区名称', key: 'name', minWidth: 160, ellipsis: { tooltip: true } },
  { title: '制式', key: 'system', width: 70 },
  { title: '带宽', key: 'band', width: 70 },
  { title: '站型', key: 'station', width: 70 },
  { title: '频段', key: 'freq', width: 90, ellipsis: { tooltip: true } },
  { title: '上行%', key: 'ul', width: 80, render: r => `${r.ul}%` },
  { title: '下行%', key: 'dl', width: 80, render: r => `${r.dl}%` },
  { title: '日均流量', key: 'flow', width: 96, render: r => `${r.flow}` },
  { title: '用户数', key: 'users', width: 80 },
  {
    title: '问题', key: 'problem', width: 110, fixed: 'right',
    render: r => h(NTag, { size: 'small', round: true, bordered: false, color: tagColor(r.problem) }, { default: () => r.problem })
  }
]);

function tagColor(problem: string) {
  const c = PROBLEM_COLOR[problem] || '#64748b';
  return { color: 'rgba(148,163,184,0.12)', textColor: c, borderColor: 'transparent' };
}
function problemClass(problem: string) {
  if (problem === '高负荷') return 'is-rose';
  if (problem === '高流量预警') return 'is-amber';
  if (problem === '利用率预警') return 'is-blue';
  return 'is-slate';
}
function rowProps(row: CellRow) {
  return { class: 'cap-row', style: 'cursor:pointer', onClick: () => openDetail(row.id) };
}

// ---------- 详情 ----------
const detailProblem = computed(() => detailValue('高负荷问题'));
const detailSuggestion = computed(() => detailValue('优化建议'));
const detailMetrics = computed(() => {
  const d = detail.value;
  if (!d) return [] as { label: string; value: string }[];
  const det = d.detail;
  const pct = (key: string) => { const v = det[key]; return v === '' || v === null || v === undefined ? '-' : `${(Number(v) * 100).toFixed(1)}%`; };
  const raw = (key: string) => { const v = det[key]; return v === '' || v === null || v === undefined ? '-' : String(v); };
  return [
    { label: d.labels.ul, value: pct(d.ul_field) },
    { label: d.labels.dl, value: pct(d.dl_field) },
    { label: '日均流量(GB)', value: raw(d.flow_field) },
    { label: '用户数', value: raw(d.users_field) },
    { label: '小区功率', value: raw('功率') },
    { label: '扇区', value: raw('扇区') },
    { label: '物理站', value: raw('物理站') },
    { label: '是否高负荷', value: raw('是否高负荷小区') }
  ];
});
function detailValue(key: string): string {
  const v = detail.value?.detail?.[key];
  return v === undefined || v === null ? '' : String(v);
}

// ---------- 数据加载 ----------
async function loadStatus() {
  loadingStatus.value = true;
  try {
    const status = await apiGet<{ ready: boolean }>('/api/dashboard/status');
    ready.value = status.ready;
    if (ready.value) await loadAll();
  } catch (error) {
    ready.value = false;
    message.error(error instanceof Error ? error.message : '加载失败');
  } finally {
    loadingStatus.value = false;
  }
}

async function loadAll() {
  await Promise.all([loadOverview(), loadCells()]);
}

async function loadOverview() {
  loadingOverview.value = true;
  try {
    const data = await apiGet<Overview>(`/api/dashboard/overview?rat=${rat.value}`);
    overview.value = data;
    animateCards(data.summary);
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载概览失败');
  } finally {
    loadingOverview.value = false;
  }
}

async function loadCells() {
  loadingCells.value = true;
  try {
    const qs = `rat=${rat.value}&problem=${encodeURIComponent(problemFilter.value)}&keyword=${encodeURIComponent(keyword.value.trim())}&page=${page.value}&page_size=${pageSize}`;
    const data = await apiGet<{ items: CellRow[]; total: number }>(`/api/dashboard/cells?${qs}`);
    cells.value = data.items;
    cellTotal.value = data.total;
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载清单失败');
  } finally {
    loadingCells.value = false;
  }
}

async function openDetail(id: string) {
  detailVisible.value = true;
  loadingDetail.value = true;
  detail.value = null;
  try {
    detail.value = await apiGet<CellDetail>(`/api/dashboard/cell?rat=${rat.value}&id=${encodeURIComponent(id)}`);
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载详情失败');
    detailVisible.value = false;
  } finally {
    loadingDetail.value = false;
  }
}

function switchRat(value: Rat) {
  if (rat.value === value) return;
  rat.value = value;
  page.value = 1;
  problemFilter.value = '';
  keyword.value = '';
  void loadAll();
}
function setProblemFilter(value: string) {
  if (problemFilter.value === value) return;
  problemFilter.value = value;
  page.value = 1;
  void loadCells();
}
function searchCells() {
  page.value = 1;
  void loadCells();
}
function changePage(value: number) {
  page.value = value;
  void loadCells();
}
function reload() {
  void loadAll();
}

onMounted(loadStatus);
</script>

<style scoped>
.cap-dashboard {
  position: relative;
  height: 100%;
  min-height: 0;
  overflow: auto;
  padding: 20px 24px 32px;
  color: #e2e8f0;
  background:
    radial-gradient(1200px 600px at 12% -10%, rgba(56, 189, 248, 0.12), transparent 60%),
    radial-gradient(1000px 600px at 100% 0%, rgba(129, 140, 248, 0.12), transparent 55%),
    linear-gradient(180deg, #0b1220 0%, #070b15 100%);
}

.cap-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 320px;
  gap: 14px;
}

.cap-empty-orb {
  width: 92px;
  height: 92px;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 40%, rgba(56, 189, 248, 0.55), rgba(56, 189, 248, 0) 70%);
  box-shadow: 0 0 60px rgba(56, 189, 248, 0.45);
  animation: pulse 2.4s ease-in-out infinite;
}
.cap-empty-text {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #e2e8f0;
}
.cap-empty-sub {
  margin: 0;
  max-width: 460px;
  text-align: center;
  font-size: 13px;
  color: #64748b;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.85; }
  50% { transform: scale(1.12); opacity: 1; }
}

.cap-body { display: flex; flex-direction: column; gap: 18px; }

.cap-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.cap-title-wrap { display: flex; align-items: center; gap: 12px; }
.cap-spark {
  width: 6px; height: 26px; border-radius: 3px;
  background: linear-gradient(180deg, #22d3ee, #818cf8);
  box-shadow: 0 0 16px rgba(56, 189, 248, 0.7);
}
.cap-title { margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 1px; color: #f1f5f9; }
.cap-sub { font-size: 12px; color: #64748b; }
.cap-controls { display: flex; align-items: center; gap: 12px; }

.cap-seg {
  display: inline-flex;
  padding: 3px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.16);
}
.cap-seg.sm { padding: 2px; border-radius: 8px; }
.cap-seg-btn {
  padding: 6px 18px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #94a3b8;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}
.cap-seg.sm .cap-seg-btn { padding: 4px 12px; font-size: 12px; }
.cap-seg-btn:hover { color: #e2e8f0; }
.cap-seg-btn.active {
  color: #061018;
  background: linear-gradient(135deg, #22d3ee, #38bdf8);
  box-shadow: 0 0 18px rgba(56, 189, 248, 0.45);
}
.cap-refresh {
  display: inline-flex; align-items: center; justify-content: center;
  width: 34px; height: 34px; border-radius: 9px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(15, 23, 42, 0.6);
  color: #94a3b8; cursor: pointer; font-size: 17px;
  transition: all 0.18s ease;
}
.cap-refresh:hover:not(:disabled) { color: #22d3ee; border-color: rgba(56, 189, 248, 0.5); box-shadow: 0 0 16px rgba(56, 189, 248, 0.3); }
.cap-refresh:disabled { opacity: 0.5; cursor: wait; }

/* 汇总卡片 */
.cap-cards {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 14px;
}
.cap-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 14px;
  background: linear-gradient(160deg, rgba(30, 41, 59, 0.55), rgba(15, 23, 42, 0.35));
  border: 1px solid rgba(148, 163, 184, 0.14);
  overflow: hidden;
  backdrop-filter: blur(8px);
  animation: cardIn 0.5s ease both;
}
@keyframes cardIn { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
.cap-card-icon {
  display: flex; align-items: center; justify-content: center;
  width: 42px; height: 42px; flex: 0 0 auto;
  border-radius: 11px; font-size: 22px;
  background: rgba(148, 163, 184, 0.1);
}
.cap-card-body { min-width: 0; }
.cap-card-value { font-size: 26px; font-weight: 800; line-height: 1.1; color: #f8fafc; font-variant-numeric: tabular-nums; }
.cap-card-unit { font-size: 13px; font-weight: 600; margin-left: 3px; color: #94a3b8; }
.cap-card-label { margin-top: 4px; font-size: 12px; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cap-card-glow { position: absolute; right: -30px; top: -30px; width: 90px; height: 90px; border-radius: 50%; opacity: 0.5; filter: blur(8px); }
.tone-cyan .cap-card-icon { color: #22d3ee; } .tone-cyan .cap-card-glow { background: rgba(34, 211, 238, 0.35); }
.tone-rose .cap-card-icon { color: #fb7185; } .tone-rose .cap-card-glow { background: rgba(251, 113, 133, 0.35); }
.tone-blue .cap-card-icon { color: #38bdf8; } .tone-blue .cap-card-glow { background: rgba(56, 189, 248, 0.32); }
.tone-amber .cap-card-icon { color: #fbbf24; } .tone-amber .cap-card-glow { background: rgba(251, 191, 36, 0.3); }
.tone-violet .cap-card-icon { color: #c084fc; } .tone-violet .cap-card-glow { background: rgba(192, 132, 252, 0.3); }
.tone-emerald .cap-card-icon { color: #34d399; } .tone-emerald .cap-card-glow { background: rgba(52, 211, 153, 0.3); }
.cap-card::after { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: currentColor; opacity: 0.5; }
.tone-cyan::after { color: #22d3ee; } .tone-rose::after { color: #fb7185; } .tone-blue::after { color: #38bdf8; }
.tone-amber::after { color: #fbbf24; } .tone-violet::after { color: #c084fc; } .tone-emerald::after { color: #34d399; }

/* 图表区 */
.cap-charts {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 14px;
}
.cap-panel {
  padding: 14px 16px;
  border-radius: 14px;
  background: linear-gradient(160deg, rgba(30, 41, 59, 0.5), rgba(15, 23, 42, 0.32));
  border: 1px solid rgba(148, 163, 184, 0.14);
  backdrop-filter: blur(8px);
}
.span-2 { grid-column: span 2; } .span-3 { grid-column: span 3; } .span-4 { grid-column: span 4; }
.cap-panel-head {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 10px; font-size: 13px; font-weight: 600; color: #cbd5e1;
}
.cap-panel-head.sm { font-size: 12px; margin: 14px 0 8px; }
.cap-panel-head .bar { width: 4px; height: 13px; border-radius: 2px; background: linear-gradient(180deg, #22d3ee, #818cf8); }

/* 清单 */
.cap-list { display: flex; flex-direction: column; }
.cap-list-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 10px; }
.cap-list-filters { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.cap-search { width: 220px; }
.cap-table { background: transparent; margin-top: 4px; }
.cap-pager { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 12px; }
.cap-pager-total { font-size: 12px; color: #64748b; }

/* 详情抽屉 */
.cap-detail-head { display: flex; align-items: baseline; gap: 10px; min-width: 0; }
.cap-detail-id { font-weight: 700; font-size: 15px; }
.cap-detail-name { font-size: 12px; color: var(--td-text-color-secondary, #94a3b8); overflow: hidden; text-overflow: ellipsis; }
.cap-detail { display: flex; flex-direction: column; gap: 16px; }
.cap-detail-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.cap-tag { padding: 3px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.cap-tag.xs { padding: 1px 8px; font-size: 11px; }
.cap-tag.plain { background: rgba(148, 163, 184, 0.16); color: var(--td-text-color-secondary, #64748b); }
.cap-tag.is-rose { background: rgba(251, 113, 133, 0.16); color: #f43f5e; }
.cap-tag.is-amber { background: rgba(251, 191, 36, 0.16); color: #d97706; }
.cap-tag.is-blue { background: rgba(56, 189, 248, 0.16); color: #0284c7; }
.cap-tag.is-slate { background: rgba(100, 116, 139, 0.16); color: #64748b; }
.cap-detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.cap-metric { padding: 10px 12px; border-radius: 10px; background: var(--td-bg-color-secondarycontainer, rgba(148, 163, 184, 0.08)); border: 1px solid var(--td-border-color-light, rgba(148, 163, 184, 0.16)); }
.cap-metric-label { font-size: 12px; color: var(--td-text-color-secondary, #94a3b8); }
.cap-metric-value { margin-top: 4px; font-size: 16px; font-weight: 700; }
.cap-suggest { padding: 12px 14px; border-radius: 12px; background: rgba(251, 191, 36, 0.08); border: 1px solid rgba(251, 191, 36, 0.3); }
.cap-suggest-head { display: flex; align-items: center; gap: 6px; font-weight: 700; color: #d97706; margin-bottom: 6px; }
.cap-suggest-text { margin: 0; font-size: 13px; line-height: 1.7; color: var(--td-text-color-primary, #334155); }
.cap-sib-list { display: flex; flex-direction: column; gap: 8px; }
.cap-sib-item { padding: 10px 12px; border-radius: 10px; border: 1px solid var(--td-border-color-light, rgba(148, 163, 184, 0.16)); }
.cap-sib-main { display: flex; align-items: baseline; gap: 8px; }
.cap-sib-id { font-weight: 600; font-size: 13px; }
.cap-sib-name { font-size: 12px; color: var(--td-text-color-secondary, #94a3b8); overflow: hidden; text-overflow: ellipsis; }
.cap-sib-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 6px; font-size: 12px; color: var(--td-text-color-secondary, #94a3b8); }

@media (max-width: 1280px) {
  .cap-cards { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .span-2, .span-3, .span-4 { grid-column: span 3; }
  .cap-charts { grid-template-columns: repeat(6, minmax(0, 1fr)); }
}
@media (max-width: 760px) {
  .cap-dashboard { padding: 14px; }
  .cap-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .span-2, .span-3, .span-4 { grid-column: span 6; }
}
</style>

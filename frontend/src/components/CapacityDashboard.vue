<template>
  <n-config-provider :theme="naiveTheme" :theme-overrides="naiveThemeOverrides">
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
        <div class="cap-overview">
          <n-spin :show="loadingOverview">
            <!-- 汇总卡片 -->
            <section class="cap-cards">
              <div
                v-for="(card, idx) in cards"
                :key="card.key"
                class="cap-card"
                :class="card.tone"
                :style="{ animationDelay: idx * 50 + 'ms' }"
              >
                <div class="cap-card-icon"><n-icon><component :is="card.icon" /></n-icon></div>
                <div class="cap-card-body">
                  <div class="cap-card-value">{{ card.display }}<span v-if="card.unit" class="cap-card-unit">{{ card.unit }}</span></div>
                  <div class="cap-card-label">{{ card.label }}</div>
                </div>
                <div class="cap-card-glow"></div>
              </div>
            </section>

            <!-- 图表区：两行三列 -->
            <section class="cap-charts">
              <div class="cap-panel">
                <div class="cap-panel-head"><span class="bar"></span>负荷问题分布</div>
                <e-chart :option="problemOption" :height="chartHeight" />
              </div>
              <div class="cap-panel">
                <div class="cap-panel-head"><span class="bar"></span>上行利用率分布（{{ overview?.labels.ul }}）</div>
                <e-chart :option="ulHistOption" :height="chartHeight" />
              </div>
              <div class="cap-panel">
                <div class="cap-panel-head"><span class="bar"></span>下行利用率分布（{{ overview?.labels.dl }}）</div>
                <e-chart :option="dlHistOption" :height="chartHeight" />
              </div>
              <div class="cap-panel">
                <div class="cap-panel-head"><span class="bar"></span>制式分布（总数 / 高负荷）</div>
                <e-chart :option="systemOption" :height="chartHeight" />
              </div>
              <div class="cap-panel">
                <div class="cap-panel-head"><span class="bar"></span>站型分布</div>
                <e-chart :option="stationOption" :height="chartHeight" />
              </div>
              <div class="cap-panel">
                <div class="cap-panel-head"><span class="bar"></span>频段标记小区 Top</div>
                <e-chart :option="freqOption" :height="chartHeight" />
              </div>
            </section>
          </n-spin>
        </div>

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
                size="small"
                clearable
                placeholder="CGI / 小区名称"
                @keyup.enter="searchCells"
                @clear="searchCells"
              >
                <template #prefix><n-icon><SearchOutline /></n-icon></template>
              </n-input>
              <n-button size="small" type="primary" ghost @click="searchCells">查询</n-button>
              <n-button size="small" tertiary :loading="exporting" :disabled="!cellTotal" @click="exportCells">
                <template #icon><n-icon><DownloadOutline /></n-icon></template>
                导出
              </n-button>
            </div>
          </div>
          <div class="cap-table-wrap">
            <n-data-table
              class="cap-table"
              size="small"
              :columns="columns"
              :data="cells"
              :loading="loadingCells"
              :bordered="false"
              :single-line="false"
              :scroll-x="1180"
              :row-props="rowProps"
              flex-height
              style="height: 100%"
            />
          </div>
          <div class="cap-pager">
            <span class="cap-pager-total">共 {{ cellTotal }} 个问题小区</span>
            <n-pagination
              :page="page"
              :page-count="pageCount"
              :page-size="pageSize"
              size="small"
              @update:page="changePage"
            />
          </div>
        </section>
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
  </n-config-provider>
</template>

<script setup lang="ts">
import { computed, h, onBeforeUnmount, onMounted, reactive, ref, watch, type Component } from 'vue';
import { NTag, darkTheme, lightTheme, useMessage } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import type { EChartsOption } from 'echarts';
import {
  ArrowDownOutline,
  ArrowUpOutline,
  BulbOutline,
  CellularOutline,
  CloudUploadOutline,
  DownloadOutline,
  FlashOutline,
  PulseOutline,
  RefreshOutline,
  SearchOutline,
  TrendingUpOutline
} from '@vicons/ionicons5';

import { apiGet, downloadGet } from '../api/client';
import { themeName } from '../composables/theme';
import { resetPageHeader, setPageHeader, type PageHeaderAction } from '../composables/pageHeader';
import EChart from './EChart.vue';

type Rat = '4g' | '5g';
interface NameVal { name: string; value: number }
interface CatStat { name: string; total: number; high: number; flagged: number }
interface HistBucket { bucket: string; value: number }
interface TopCell { id: string; name: string; system: string; band: string; station: string; ul: number; dl: number; flow: number; users: number; problem: string }
interface Overview {
  rat: string;
  labels: { ul: string; dl: string };
  summary: { total: number; high_load: number; util_warn: number; flow_warn: number; normal: number; avg_ul: number; avg_dl: number; max_dl: number; avg_flow: number; total_flow: number };
  problem_pie: NameVal[];
  by_system: CatStat[];
  by_station: CatStat[];
  by_freq: CatStat[];
  ul_hist: HistBucket[];
  dl_hist: HistBucket[];
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

// ---------- 主题（跟随应用日/夜切换） ----------
const isLight = computed(() => themeName.value === 'light');
const naiveTheme = computed(() => (isLight.value ? lightTheme : darkTheme));

// 看板内 Naive 组件配色覆盖：青色强调色 + 对应明暗底色
const naiveDark = {
  common: { primaryColor: '#22d3ee', primaryColorHover: '#38bdf8', primaryColorPressed: '#0891b2', primaryColorSuppl: '#38bdf8', borderRadius: '8px' },
  DataTable: {
    thColor: 'rgba(30, 41, 59, 0.85)', thColorHover: 'rgba(30, 41, 59, 0.95)', thTextColor: '#cbd5e1', thFontWeight: '600',
    tdColor: 'transparent', tdColorHover: 'rgba(56, 189, 248, 0.08)', tdTextColor: '#dbe4f0',
    borderColor: 'rgba(148, 163, 184, 0.12)', loadingColor: 'rgba(8, 14, 26, 0.6)'
  },
  Input: {
    color: 'rgba(15, 23, 42, 0.45)', colorFocus: 'rgba(15, 23, 42, 0.7)',
    border: '1px solid rgba(148, 163, 184, 0.18)', borderHover: '1px solid rgba(56, 189, 248, 0.5)', borderFocus: '1px solid rgba(56, 189, 248, 0.7)',
    boxShadowFocus: '0 0 0 2px rgba(56, 189, 248, 0.18)', textColor: '#e2e8f0', placeholderColor: '#64748b'
  },
  Pagination: {
    itemColor: 'rgba(15, 23, 42, 0.4)', itemColorHover: 'rgba(56, 189, 248, 0.12)', itemColorPressed: 'rgba(56, 189, 248, 0.18)', itemColorActive: 'rgba(56, 189, 248, 0.16)',
    itemBorder: '1px solid rgba(148, 163, 184, 0.16)', itemBorderActive: '1px solid #22d3ee',
    itemTextColor: '#94a3b8', itemTextColorHover: '#e2e8f0', itemTextColorActive: '#22d3ee'
  },
  Drawer: { color: '#0c1422' },
  Empty: { textColor: '#64748b', iconColor: '#475569' }
};
const naiveLight = {
  common: { primaryColor: '#0891b2', primaryColorHover: '#06b6d4', primaryColorPressed: '#0e7490', primaryColorSuppl: '#06b6d4', borderRadius: '8px' },
  DataTable: {
    thColor: 'rgba(241, 245, 249, 0.9)', thColorHover: 'rgba(226, 232, 240, 0.95)', thTextColor: '#475569', thFontWeight: '600',
    tdColor: 'transparent', tdColorHover: 'rgba(8, 145, 178, 0.07)', tdTextColor: '#334155',
    borderColor: 'rgba(15, 23, 42, 0.08)', loadingColor: 'rgba(255, 255, 255, 0.6)'
  },
  Input: {
    color: 'rgba(255, 255, 255, 0.85)', colorFocus: '#ffffff',
    border: '1px solid rgba(15, 23, 42, 0.12)', borderHover: '1px solid rgba(8, 145, 178, 0.5)', borderFocus: '1px solid rgba(8, 145, 178, 0.7)',
    boxShadowFocus: '0 0 0 2px rgba(8, 145, 178, 0.15)', textColor: '#1e293b', placeholderColor: '#94a3b8'
  },
  Pagination: {
    itemColor: 'rgba(255, 255, 255, 0.7)', itemColorHover: 'rgba(8, 145, 178, 0.08)', itemColorPressed: 'rgba(8, 145, 178, 0.14)', itemColorActive: 'rgba(8, 145, 178, 0.12)',
    itemBorder: '1px solid rgba(15, 23, 42, 0.12)', itemBorderActive: '1px solid #0891b2',
    itemTextColor: '#64748b', itemTextColorHover: '#1e293b', itemTextColorActive: '#0891b2'
  },
  Drawer: { color: '#ffffff' },
  Empty: { textColor: '#94a3b8', iconColor: '#cbd5e1' }
};
const naiveThemeOverrides = computed(() => (isLight.value ? naiveLight : naiveDark));

// ECharts 明暗配色
const chartPalette = computed(() => (isLight.value
  ? { axisText: '#64748b', axisLine: 'rgba(15,23,42,0.15)', splitLine: 'rgba(15,23,42,0.06)', tooltipBg: 'rgba(255,255,255,0.97)', tooltipText: '#1e293b', tooltipBorder: 'rgba(8,145,178,0.4)', legend: '#64748b', pieBorder: '#ffffff', barTrack: 'rgba(8,145,178,0.18)' }
  : { axisText: '#94a3b8', axisLine: 'rgba(148,163,184,0.25)', splitLine: 'rgba(148,163,184,0.12)', tooltipBg: 'rgba(15,23,42,0.92)', tooltipText: '#e2e8f0', tooltipBorder: 'rgba(56,189,248,0.35)', legend: '#94a3b8', pieBorder: 'rgba(2,6,23,0.6)', barTrack: 'rgba(56,189,248,0.18)' }
));

const chartHeight = 'clamp(108px, 13vh, 160px)';

const loadingStatus = ref(true);
const ready = ref(false);
const rat = ref<Rat>('5g');

const loadingOverview = ref(false);
const overview = ref<Overview | null>(null);

const cells = ref<CellRow[]>([]);
const cellTotal = ref(0);
const page = ref(1);
const pageSize = 20;
const loadingCells = ref(false);
const problemFilter = ref('');
const keyword = ref('');
const exporting = ref(false);
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
  正常: '#94a3b8'
};

// ---------- 汇总卡片（含数字滚动） ----------
const animated = reactive<Record<string, number>>({ total: 0, high_load: 0, util_warn: 0, flow_warn: 0, avg_ul: 0, avg_dl: 0, total_flow: 0 });

const cards = computed(() => {
  const defs: { key: keyof typeof animated; label: string; icon: Component; tone: string; unit?: string; digits?: number; flow?: boolean }[] = [
    { key: 'total', label: '小区总数', icon: CellularOutline, tone: 'tone-cyan' },
    { key: 'high_load', label: '高负荷小区', icon: FlashOutline, tone: 'tone-rose' },
    { key: 'util_warn', label: '利用率预警', icon: PulseOutline, tone: 'tone-blue' },
    { key: 'flow_warn', label: '高流量预警', icon: TrendingUpOutline, tone: 'tone-amber' },
    { key: 'avg_ul', label: '平均上行利用率', icon: ArrowUpOutline, tone: 'tone-violet', unit: '%', digits: 1 },
    { key: 'avg_dl', label: '平均下行利用率', icon: ArrowDownOutline, tone: 'tone-cyan', unit: '%', digits: 1 },
    { key: 'total_flow', label: '总日均流量', icon: CloudUploadOutline, tone: 'tone-emerald', flow: true }
  ];
  return defs.map(d => {
    if (d.flow) {
      const f = formatFlow(animated[d.key]);
      return { ...d, display: f.value, unit: f.unit };
    }
    return { ...d, display: formatNum(animated[d.key], d.digits ?? 0) };
  });
});

function formatNum(value: number, digits: number): string {
  const fixed = Number(value).toFixed(digits);
  const [int, dec] = fixed.split('.');
  const withSep = int.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return dec ? `${withSep}.${dec}` : withSep;
}

// 入参单位为 GB，自动换算到合适单位（B/KB/MB/GB/TB/PB）
function formatFlow(gb: number): { value: string; unit: string } {
  const v = Number(gb) || 0;
  if (v >= 1) {
    const units = ['GB', 'TB', 'PB', 'EB'];
    let i = 0;
    let n = v;
    while (n >= 1024 && i < units.length - 1) { n /= 1024; i += 1; }
    const digits = n >= 100 ? 0 : n >= 10 ? 1 : 2;
    return { value: formatNum(n, digits), unit: units[i] };
  }
  const units = ['GB', 'MB', 'KB', 'B'];
  let i = 0;
  let n = v;
  while (n < 1 && i < units.length - 1) { n *= 1024; i += 1; }
  const digits = n >= 100 ? 0 : 1;
  return { value: formatNum(n, digits), unit: units[i] };
}

function animateCards(s: Overview['summary']) {
  const targets: Record<string, number> = {
    total: s.total, high_load: s.high_load, util_warn: s.util_warn,
    flow_warn: s.flow_warn, avg_ul: s.avg_ul, avg_dl: s.avg_dl, total_flow: s.total_flow
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
  return { left: 8, right: 16, top: 24, bottom: 6, containLabel: true };
}
function axisLine() {
  return { lineStyle: { color: chartPalette.value.axisLine } };
}
function axisLabel() {
  return { color: chartPalette.value.axisText, fontSize: 11 };
}
function splitLine() {
  return { lineStyle: { color: chartPalette.value.splitLine } };
}
function tooltipBase(): EChartsOption['tooltip'] {
  const p = chartPalette.value;
  return {
    backgroundColor: p.tooltipBg,
    borderColor: p.tooltipBorder,
    borderWidth: 1,
    textStyle: { color: p.tooltipText, fontSize: 12 }
  };
}
function legendStyle() {
  return { color: chartPalette.value.legend, fontSize: 11 };
}
// 矮图表的数值轴缩写，避免刻度文字过长 / 纵向重叠
function abbrNum(v: number): string {
  const n = Math.abs(v);
  if (n >= 1e8) return `${(v / 1e8).toFixed(1).replace(/\.0$/, '')}亿`;
  if (n >= 1e4) return `${(v / 1e4).toFixed(1).replace(/\.0$/, '')}万`;
  if (n >= 1e3) return `${(v / 1e3).toFixed(1).replace(/\.0$/, '')}k`;
  return String(v);
}
function valueAxis(): EChartsOption['yAxis'] {
  return { type: 'value', splitNumber: 3, splitLine: splitLine(), axisLabel: { ...axisLabel(), formatter: (v: number) => abbrNum(v) } };
}

const problemOption = computed<EChartsOption>(() => {
  const data = (overview.value?.problem_pie || []).map(d => ({
    name: d.name, value: d.value,
    itemStyle: { color: PROBLEM_COLOR[d.name] || '#64748b' }
  }));
  return {
    tooltip: { ...tooltipBase(), trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: legendStyle(), icon: 'circle', itemWidth: 9, itemHeight: 9 },
    series: [{
      type: 'pie', radius: ['46%', '72%'], center: ['50%', '42%'], avoidLabelOverlap: true,
      itemStyle: { borderColor: chartPalette.value.pieBorder, borderWidth: 2 },
      label: { show: false }, labelLine: { show: false },
      data
    }]
  };
});

function makeHist(buckets: HistBucket[], c0: string, c1: string): EChartsOption {
  return {
    tooltip: { ...tooltipBase(), trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: baseGrid(),
    xAxis: { type: 'category', data: buckets.map(b => b.bucket), axisLine: axisLine(), axisLabel: { ...axisLabel(), rotate: 30 }, axisTick: { show: false } },
    yAxis: valueAxis(),
    series: [{
      type: 'bar', barWidth: '58%', data: buckets.map(b => b.value),
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: c0 }, { offset: 1, color: c1 }] }
      }
    }]
  };
}
const ulHistOption = computed<EChartsOption>(() => makeHist(overview.value?.ul_hist || [], '#818cf8', 'rgba(129,140,248,0.15)'));
const dlHistOption = computed<EChartsOption>(() => makeHist(overview.value?.dl_hist || [], '#22d3ee', 'rgba(56,189,248,0.15)'));

const systemOption = computed<EChartsOption>(() => {
  const stats = overview.value?.by_system || [];
  return {
    tooltip: { ...tooltipBase(), trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, right: 0, textStyle: legendStyle(), itemWidth: 10, itemHeight: 10 },
    grid: baseGrid(),
    xAxis: { type: 'category', data: stats.map(s => s.name), axisLine: axisLine(), axisLabel: { ...axisLabel(), interval: 0, rotate: stats.length > 5 ? 24 : 0 }, axisTick: { show: false } },
    yAxis: valueAxis(),
    series: [
      { name: '总数', type: 'bar', barGap: '-100%', barWidth: '46%', itemStyle: { borderRadius: [3, 3, 0, 0], color: chartPalette.value.barTrack }, data: stats.map(s => s.total) },
      { name: '高负荷', type: 'bar', barWidth: '46%', itemStyle: { borderRadius: [3, 3, 0, 0], color: '#fb7185' }, data: stats.map(s => s.high) }
    ]
  };
});

const stationOption = computed<EChartsOption>(() => {
  const data = (overview.value?.by_station || []).map((s, i) => ({ name: s.name, value: s.total, itemStyle: { color: PALETTE[i % PALETTE.length] } }));
  return {
    tooltip: { ...tooltipBase(), trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: legendStyle(), icon: 'circle', itemWidth: 9, itemHeight: 9 },
    series: [{
      type: 'pie', radius: ['42%', '70%'], center: ['50%', '42%'],
      itemStyle: { borderColor: chartPalette.value.pieBorder, borderWidth: 2 },
      label: { show: false }, labelLine: { show: false }, data
    }]
  };
});

const freqOption = computed<EChartsOption>(() => {
  const stats = [...(overview.value?.by_freq || [])].sort((a, b) => a.flagged - b.flagged);
  return {
    tooltip: { ...tooltipBase(), trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 8, right: 24, top: 10, bottom: 6, containLabel: true },
    xAxis: { type: 'value', splitNumber: 3, splitLine: splitLine(), axisLabel: { ...axisLabel(), formatter: (v: number) => abbrNum(v) } },
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
  return { color: isLight.value ? 'rgba(100,116,139,0.1)' : 'rgba(148,163,184,0.14)', textColor: c, borderColor: 'transparent' };
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

async function exportCells() {
  if (!cellTotal.value) return;
  exporting.value = true;
  try {
    const qs = `rat=${rat.value}&problem=${encodeURIComponent(problemFilter.value)}&keyword=${encodeURIComponent(keyword.value.trim())}`;
    const filename = `问题小区清单_${rat.value.toUpperCase()}.csv`;
    const result = await downloadGet(`/api/dashboard/export?${qs}`, filename);
    if (result.saved) message.success('问题小区清单已导出');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '导出失败');
  } finally {
    exporting.value = false;
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

// ---------- 顶部框架页头（标题/制式切换/刷新） ----------
function buildHeaderActions(): PageHeaderAction[] {
  return [
    { key: 'rat-4g', label: '4G', type: rat.value === '4g' ? 'primary' : 'default', variant: rat.value === '4g' ? 'solid' : 'outline', onClick: () => switchRat('4g') },
    { key: 'rat-5g', label: '5G', type: rat.value === '5g' ? 'primary' : 'default', variant: rat.value === '5g' ? 'solid' : 'outline', onClick: () => switchRat('5g') },
    { key: 'dashboard-refresh', label: '刷新', icon: RefreshOutline, variant: 'outline', loading: loadingOverview, disabled: loadingOverview, onClick: reload }
  ];
}
function applyPageHeader() {
  if (!ready.value) {
    resetPageHeader();
    return;
  }
  setPageHeader({ subtitle: '高负荷小区分析 · 实时数据', actions: buildHeaderActions() });
}
watch([rat, ready], applyPageHeader);

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
onBeforeUnmount(resetPageHeader);
</script>

<style scoped>
/* 主题变量定义在 documentElement 上，使 teleport 到 body 的详情抽屉也能继承 */
:global([data-theme='dark']) {
  --cap-bg:
    radial-gradient(1200px 600px at 12% -10%, rgba(56, 189, 248, 0.12), transparent 60%),
    radial-gradient(1000px 600px at 100% 0%, rgba(129, 140, 248, 0.12), transparent 55%),
    linear-gradient(180deg, #0b1220 0%, #070b15 100%);
  --cap-panel-bg: linear-gradient(160deg, rgba(30, 41, 59, 0.5), rgba(15, 23, 42, 0.32));
  --cap-card-bg: linear-gradient(160deg, rgba(30, 41, 59, 0.55), rgba(15, 23, 42, 0.35));
  --cap-panel-border: rgba(148, 163, 184, 0.14);
  --cap-shadow: none;
  --cap-icon-bg: rgba(148, 163, 184, 0.1);
  --cap-control-bg: rgba(15, 23, 42, 0.6);
  --cap-control-border: rgba(148, 163, 184, 0.16);
  --cap-text: #e2e8f0;
  --cap-text-strong: #f1f5f9;
  --cap-text-sub: #94a3b8;
  --cap-text-muted: #64748b;
  --cap-soft-bg: rgba(148, 163, 184, 0.08);
  --cap-tag-plain-bg: rgba(148, 163, 184, 0.16);
  --cap-glow-opacity: 0.5;
}
:global([data-theme='light']) {
  --cap-bg:
    radial-gradient(1200px 600px at 12% -10%, rgba(56, 189, 248, 0.16), transparent 60%),
    radial-gradient(1000px 600px at 100% 0%, rgba(129, 140, 248, 0.14), transparent 55%),
    linear-gradient(180deg, #eef2f9 0%, #e3e9f3 100%);
  --cap-panel-bg: rgba(255, 255, 255, 0.82);
  --cap-card-bg: rgba(255, 255, 255, 0.9);
  --cap-panel-border: rgba(15, 23, 42, 0.08);
  --cap-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
  --cap-icon-bg: rgba(15, 23, 42, 0.05);
  --cap-control-bg: rgba(255, 255, 255, 0.7);
  --cap-control-border: rgba(15, 23, 42, 0.1);
  --cap-text: #334155;
  --cap-text-strong: #0f172a;
  --cap-text-sub: #64748b;
  --cap-text-muted: #94a3b8;
  --cap-soft-bg: rgba(15, 23, 42, 0.04);
  --cap-tag-plain-bg: rgba(15, 23, 42, 0.06);
  --cap-glow-opacity: 0.32;
}

.cap-dashboard {
  position: relative;
  height: calc(100vh - 64px);
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 14px 18px;
  color: var(--cap-text);
  background: var(--cap-bg);
}

.cap-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 0;
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
  color: var(--cap-text-strong);
}
.cap-empty-sub {
  margin: 0;
  max-width: 460px;
  text-align: center;
  font-size: 13px;
  color: var(--cap-text-muted);
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.85; }
  50% { transform: scale(1.12); opacity: 1; }
}

.cap-body { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 12px; }

.cap-seg {
  display: inline-flex;
  padding: 3px;
  border-radius: 10px;
  background: var(--cap-control-bg);
  border: 1px solid var(--cap-control-border);
}
.cap-seg.sm { padding: 2px; border-radius: 8px; }
.cap-seg-btn {
  padding: 5px 16px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--cap-text-sub);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}
.cap-seg.sm .cap-seg-btn { padding: 4px 12px; font-size: 12px; }
.cap-seg-btn:hover { color: var(--cap-text-strong); }
.cap-seg-btn.active {
  color: #061018;
  background: linear-gradient(135deg, #22d3ee, #38bdf8);
  box-shadow: 0 0 18px rgba(56, 189, 248, 0.45);
}

/* 概览区（卡片 + 图表），固定高度，由 n-spin 包裹 */
.cap-overview { flex: 0 0 auto; }
.cap-overview :deep(.n-spin-content) { display: flex; flex-direction: column; gap: 12px; }

/* 汇总卡片 */
.cap-cards {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 10px;
}
.cap-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: var(--cap-card-bg);
  border: 1px solid var(--cap-panel-border);
  box-shadow: var(--cap-shadow);
  overflow: hidden;
  backdrop-filter: blur(8px);
  animation: cardIn 0.5s ease both;
}
@keyframes cardIn { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
.cap-card-icon {
  display: flex; align-items: center; justify-content: center;
  width: 34px; height: 34px; flex: 0 0 auto;
  border-radius: 9px; font-size: 18px;
  background: var(--cap-icon-bg);
}
.cap-card-body { min-width: 0; }
.cap-card-value { font-size: 19px; font-weight: 800; line-height: 1.15; color: var(--cap-text-strong); font-variant-numeric: tabular-nums; white-space: nowrap; }
.cap-card-unit { font-size: 11px; font-weight: 600; margin-left: 2px; color: var(--cap-text-sub); }
.cap-card-label { margin-top: 2px; font-size: 11px; color: var(--cap-text-sub); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cap-card-glow { position: absolute; right: -30px; top: -30px; width: 90px; height: 90px; border-radius: 50%; opacity: var(--cap-glow-opacity); filter: blur(8px); }
.tone-cyan .cap-card-icon { color: #06b6d4; } .tone-cyan .cap-card-glow { background: rgba(34, 211, 238, 0.35); }
.tone-rose .cap-card-icon { color: #f43f5e; } .tone-rose .cap-card-glow { background: rgba(251, 113, 133, 0.35); }
.tone-blue .cap-card-icon { color: #0ea5e9; } .tone-blue .cap-card-glow { background: rgba(56, 189, 248, 0.32); }
.tone-amber .cap-card-icon { color: #f59e0b; } .tone-amber .cap-card-glow { background: rgba(251, 191, 36, 0.3); }
.tone-violet .cap-card-icon { color: #8b5cf6; } .tone-violet .cap-card-glow { background: rgba(192, 132, 252, 0.3); }
.tone-emerald .cap-card-icon { color: #10b981; } .tone-emerald .cap-card-glow { background: rgba(52, 211, 153, 0.3); }
.cap-card::after { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: currentColor; opacity: 0.55; }
.tone-cyan::after { color: #06b6d4; } .tone-rose::after { color: #f43f5e; } .tone-blue::after { color: #0ea5e9; }
.tone-amber::after { color: #f59e0b; } .tone-violet::after { color: #8b5cf6; } .tone-emerald::after { color: #10b981; }

/* 图表区：两行三列 */
.cap-charts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.cap-panel {
  padding: 10px 14px;
  border-radius: 12px;
  background: var(--cap-panel-bg);
  border: 1px solid var(--cap-panel-border);
  box-shadow: var(--cap-shadow);
  backdrop-filter: blur(8px);
}
.cap-panel-head {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 4px; font-size: 13px; font-weight: 600; color: var(--cap-text);
}
.cap-panel-head.sm { font-size: 12px; margin: 14px 0 8px; }
.cap-panel-head .bar { width: 4px; height: 13px; border-radius: 2px; background: linear-gradient(180deg, #22d3ee, #818cf8); }

/* 清单：占据剩余高度，表体内部滚动（表头固定） */
.cap-list { flex: 1 1 0; min-height: 0; display: flex; flex-direction: column; padding-bottom: 10px; }
.cap-list-head { flex: 0 0 auto; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 8px; }
.cap-list-head .cap-panel-head { margin-bottom: 0; }
.cap-list-filters { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.cap-search { width: 200px; }
.cap-table-wrap { flex: 1 1 0; min-height: 0; }
.cap-table { height: 100%; background: transparent; }
.cap-pager { flex: 0 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 10px; }
.cap-pager-total { font-size: 12px; color: var(--cap-text-muted); }

/* 详情抽屉 */
.cap-detail-head { display: flex; align-items: baseline; gap: 10px; min-width: 0; }
.cap-detail-id { font-weight: 700; font-size: 15px; color: var(--cap-text-strong); }
.cap-detail-name { font-size: 12px; color: var(--cap-text-sub); overflow: hidden; text-overflow: ellipsis; }
.cap-detail { display: flex; flex-direction: column; gap: 16px; }
.cap-detail-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.cap-tag { padding: 3px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.cap-tag.xs { padding: 1px 8px; font-size: 11px; }
.cap-tag.plain { background: var(--cap-tag-plain-bg); color: var(--cap-text-sub); }
.cap-tag.is-rose { background: rgba(251, 113, 133, 0.18); color: #f43f5e; }
.cap-tag.is-amber { background: rgba(251, 191, 36, 0.18); color: #d97706; }
.cap-tag.is-blue { background: rgba(56, 189, 248, 0.18); color: #0284c7; }
.cap-tag.is-slate { background: rgba(100, 116, 139, 0.18); color: #64748b; }
.cap-detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.cap-metric { padding: 10px 12px; border-radius: 10px; background: var(--cap-soft-bg); border: 1px solid var(--cap-panel-border); }
.cap-metric-label { font-size: 12px; color: var(--cap-text-sub); }
.cap-metric-value { margin-top: 4px; font-size: 16px; font-weight: 700; color: var(--cap-text-strong); }
.cap-suggest { padding: 12px 14px; border-radius: 12px; background: rgba(251, 191, 36, 0.1); border: 1px solid rgba(251, 191, 36, 0.32); }
.cap-suggest-head { display: flex; align-items: center; gap: 6px; font-weight: 700; color: #d97706; margin-bottom: 6px; }
.cap-suggest-text { margin: 0; font-size: 13px; line-height: 1.7; color: var(--cap-text); }
.cap-sib-list { display: flex; flex-direction: column; gap: 8px; }
.cap-sib-item { padding: 10px 12px; border-radius: 10px; border: 1px solid var(--cap-panel-border); background: var(--cap-soft-bg); }
.cap-sib-main { display: flex; align-items: baseline; gap: 8px; }
.cap-sib-id { font-weight: 600; font-size: 13px; color: var(--cap-text); }
.cap-sib-name { font-size: 12px; color: var(--cap-text-sub); overflow: hidden; text-overflow: ellipsis; }
.cap-sib-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 6px; font-size: 12px; color: var(--cap-text-sub); }

@media (max-width: 1366px) {
  .cap-card-value { font-size: 17px; }
  .cap-card-icon { width: 30px; height: 30px; font-size: 16px; }
}
@media (max-width: 1180px) {
  .cap-dashboard { height: auto; min-height: calc(100vh - 64px); overflow: auto; }
  .cap-cards { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .cap-charts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .cap-list { min-height: 360px; }
}
@media (max-width: 720px) {
  .cap-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .cap-charts { grid-template-columns: minmax(0, 1fr); }
}
</style>

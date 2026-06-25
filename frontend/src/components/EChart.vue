<template>
  <div ref="host" class="echart" :style="{ height: height || '300px' }"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import * as echarts from 'echarts';

const props = defineProps<{ option: echarts.EChartsOption; height?: string }>();

const host = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;
let observer: ResizeObserver | null = null;

onMounted(() => {
  if (!host.value) return;
  chart = echarts.init(host.value, undefined, { renderer: 'canvas' });
  chart.setOption(props.option);
  observer = new ResizeObserver(() => chart?.resize());
  observer.observe(host.value);
});

watch(
  () => props.option,
  option => {
    chart?.setOption(option, true);
  },
  { deep: true }
);

onBeforeUnmount(() => {
  observer?.disconnect();
  observer = null;
  chart?.dispose();
  chart = null;
});
</script>

<style scoped>
.echart {
  width: 100%;
}
</style>

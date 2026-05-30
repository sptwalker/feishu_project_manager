<template>
  <div ref="el" class="chart" :style="{ height: height + 'px' }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echartsNs from 'echarts/core'
import { PieChart, BarChart } from 'echarts/charts'
import {
  TooltipComponent, LegendComponent, GridComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

// ECharts 的 core 类型在 vue-tsc 2.x 下会触发「过深的类型实例化」(TS2589)，
// 因此将其命名空间整体以 any 持有，避免在用户代码中实例化这些超深类型。
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const echarts: any = echartsNs

echarts.use([
  PieChart, BarChart,
  TooltipComponent, LegendComponent, GridComponent,
  CanvasRenderer,
])

const props = withDefaults(defineProps<{ option: Record<string, unknown>; height?: number }>(), {
  height: 240,
})

const el = ref<HTMLElement | null>(null)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let chart: any = null

function render() {
  if (!el.value) return
  if (!chart) chart = echarts.init(el.value)
  chart.setOption(props.option, true)
}

function onResize() {
  chart?.resize()
}

onMounted(async () => {
  await nextTick()
  render()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
})

// 图表 option 来自 computed，每次重算返回新对象引用，浅监听即可
watch(() => props.option, render)
</script>

<style scoped>
.chart { width: 100%; }
</style>

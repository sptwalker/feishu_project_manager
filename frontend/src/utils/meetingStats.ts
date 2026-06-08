/* 汇报人用时柱状图 ECharts option 生成（秒 → mm:ss）。
   供「会议中查看统计」与「会议结束统计」复用，避免两处重复。 */
export function buildPersonTimesBarOption(
  items: { name: string; seconds: number }[],
): Record<string, unknown> {
  const names = items.map((x) => x.name)
  const values = items.map((x) => x.seconds)
  // 秒 → m:ss 文本
  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`
  const palette = ['#1A73E8', '#2F8FE0', '#13C2C2', '#3B6FE0', '#5AB1BB', '#2F54EB', '#41B0D8', '#6979F8']
  return {
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (p: { name: string; value: number }[]) => `${p[0].name}：${fmt(p[0].value)}`,
    },
    grid: { left: 8, right: 24, top: 16, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category', data: names,
      axisLabel: { interval: 0, rotate: names.length > 6 ? 35 : 0 },
    },
    yAxis: {
      type: 'value', name: '用时',
      axisLabel: { formatter: (v: number) => fmt(v) },
    },
    series: [{
      type: 'bar', barWidth: '46%',
      data: values.map((v, i) => ({
        value: v,
        itemStyle: { color: palette[i % palette.length], borderRadius: [4, 4, 0, 0] },
      })),
      label: { show: true, position: 'top', formatter: (p: { value: number }) => fmt(p.value) },
    }],
  }
}

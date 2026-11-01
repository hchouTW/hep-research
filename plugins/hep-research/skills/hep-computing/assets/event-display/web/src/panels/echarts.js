// ECharts panel: draws a precomputed table as bars. Only the listed parts of ECharts are registered.
import * as echarts from 'echarts/core';
import { BarChart } from 'echarts/charts';
import { GridComponent, LegendComponent, TitleComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([BarChart, GridComponent, LegendComponent, TitleComponent, TooltipComponent, CanvasRenderer]);

const OPTION_KEYS = new Set(['title', 'tooltip', 'legend', 'xAxis', 'yAxis', 'series']);
const SERIES_KEYS = new Set(['type', 'name', 'data']);

export function validate(p) {
  if (p.integration !== 'echarts' || !p.option) throw new Error('not an echarts payload');
  for (const k of Object.keys(p.option)) {
    if (!OPTION_KEYS.has(k)) throw new Error(`echarts option '${k}' is not allowed`);   // no dataset/transform
  }
  for (const s of p.option.series) {
    for (const k of Object.keys(s)) if (!SERIES_KEYS.has(k)) throw new Error(`echarts series '${k}' is not allowed`); // no stack
    if (s.type !== 'bar') throw new Error(`echarts series type '${s.type}' is not allowed`);
  }
}

export async function mount(el, p) {
  const chart = echarts.init(el);
  chart.setOption(structuredClone(p.option));
  const onResize = () => chart.resize();
  window.addEventListener('resize', onResize);
  return {
    readback: () => {
      const o = chart.getOption();
      return { categories: o.xAxis[0].data, series: o.series.map((s) => ({ name: s.name, data: s.data })) };
    },
    dispose: () => { window.removeEventListener('resize', onResize); chart.dispose(); },
  };
}

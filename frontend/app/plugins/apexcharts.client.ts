/**
 * ApexCharts Client-Only Plugin
 *
 * The `.client.ts` suffix ensures this plugin ONLY runs on the client side.
 * This prevents "window is not defined" errors during SSR since ApexCharts
 * requires the DOM.
 *
 * Sets global ApexCharts defaults via window.Apex - all charts inherit these.
 * Individual charts can override any option.
 *
 * @see https://github.com/nuxt/nuxt/discussions/16482
 * @see https://github.com/BayBreezy/ui-thing (reference implementation)
 */
import VueApexCharts from 'vue3-apexcharts'
import type { ApexOptions } from 'apexcharts'

declare global {
  interface Window {
    Apex: ApexOptions
  }
}

/**
 * Global ApexCharts defaults - all charts inherit these.
 * Individual components only need to override what's unique to them.
 *
 * Note: ApexCharts doesn't handle OKLCH colors well. For colors that need to
 * change with theme, components should read computed CSS values at runtime.
 * CSS variables work for some properties (foreColor, borderColor) but not colors[].
 */
window.Apex = {
  chart: {
    animations: {
      enabled: true,
      speed: 300,
      dynamicAnimation: { enabled: true, speed: 300 },
    },
    fontFamily: 'var(--font-sans)',
    foreColor: 'var(--color-foreground)',
    toolbar: { show: false },
    zoom: { enabled: false },
  },
  dataLabels: { enabled: false },
  legend: { show: false },
  fill: { opacity: 0.85, type: 'solid' },
  grid: {
    borderColor: 'var(--color-border)',
    strokeDashArray: 4,
    padding: { left: 0, right: 0, top: 0, bottom: 0 },
  },
  xaxis: {
    axisBorder: { show: false },
    axisTicks: { show: false },
    labels: {
      style: { colors: 'var(--color-muted-foreground)', fontSize: '11px' },
      hideOverlappingLabels: true,
    },
  },
  yaxis: {
    labels: {
      style: { colors: 'var(--color-muted-foreground)', fontSize: '11px' },
    },
  },
  states: {
    hover: { filter: { type: 'darken' } },
    active: {
      allowMultipleDataPointsSelection: false,
      filter: { type: 'darken' },
    },
  },
}

export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.use(VueApexCharts)
})

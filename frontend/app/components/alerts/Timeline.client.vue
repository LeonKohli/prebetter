<script setup lang="ts">
/**
 * AlertsTimeline.client.vue - Interactive bar chart showing alert volume over time
 *
 * Features:
 * - Click on bar to filter table to that time period
 * - Drag to zoom/select a time range
 * - Custom reset button
 *
 * Note: Most styling comes from window.Apex in apexcharts.client.ts plugin.
 * This component only overrides what's unique to this specific chart.
 */
import type { ApexOptions } from 'apexcharts'
import { useDebounceFn, useWindowSize } from '@vueuse/core'

interface ChartInstance {
  updateOptions(options: ApexOptions, redrawPaths?: boolean, animate?: boolean): Promise<void>
  resetSeries(): void
}

const urlState = useNavigableUrlState({
  defaultView: 'grouped',
  defaultPageSize: 100,
  defaultSortBy: 'detected_at',
  defaultSortOrder: 'desc',
})

const colorMode = useColorMode()
const { width } = useWindowSize()

const {
  pending,
  chartSeries,
  totalAlerts,
  timeFrame,
  dateRange,
  getActivePresetId,
} = useTimelineData(urlState)

const chartRef = useTemplateRef<ChartInstance>('chart')
const isMobile = computed(() => width.value < 768)
const chartHeight = computed(() => isMobile.value ? 140 : 180)

const hasCustomDateRange = computed(() => {
  const filters = urlState.filters.value
  return !!(filters.start_date && filters.end_date && !getActivePresetId())
})

// Chart color from design system (--chart-1 changes between light/dark)
const chartColor = ref(getChartColor(1))

// Update chart color when theme changes
watch(() => colorMode.value, () => {
  nextTick(() => {
    chartColor.value = getChartColor(1)
  })
})

// Only override what's unique to this chart - rest comes from window.Apex
const chartOptions = computed<ApexOptions>(() => ({
  chart: {
    id: 'alerts-timeline',
    background: 'transparent',
    zoom: {
      enabled: !isMobile.value,
      type: 'x',
      autoScaleYaxis: true,
    },
    events: {
      zoomed: handleZoomed,
      dataPointSelection: handleBarClick,
    },
  },
  plotOptions: {
    bar: { borderRadius: 3, columnWidth: '80%' },
  },
  xaxis: {
    type: 'datetime',
    min: dateRange.value.start.getTime(),
    max: dateRange.value.end.getTime(),
    labels: { datetimeUTC: false },
    crosshairs: {
      width: 'barWidth',
      fill: { type: 'solid', color: 'var(--color-muted)' },
      opacity: 0.3,
    },
  },
  yaxis: {
    min: 0,
    labels: { formatter: (val: number) => Math.round(val).toString() },
  },
  tooltip: {
    theme: colorMode.value,
    shared: true,
    intersect: false,
    x: { format: 'dd MMM HH:mm' },
    y: { formatter: (val: number) => `${val} alert${val !== 1 ? 's' : ''}` },
  },
  colors: [chartColor.value],
}))

/** Update URL filters with new date range, clearing any preset */
function setDateRange(start: Date, end: Date) {
  const newFilters = { ...urlState.filters.value }
  delete (newFilters as Record<string, unknown>).date_preset
  newFilters.start_date = start.toISOString()
  newFilters.end_date = end.toISOString()
  urlState.filters.value = newFilters
}

const debouncedSetDateRange = useDebounceFn(setDateRange, 300)

function handleZoomed(_: unknown, { xaxis }: { xaxis: { min: number; max: number } }) {
  if (xaxis.min && xaxis.max && xaxis.max > xaxis.min) {
    debouncedSetDateRange(new Date(xaxis.min), new Date(xaxis.max))
  }
}

function handleBarClick(_: unknown, __: unknown, { dataPointIndex }: { dataPointIndex: number }) {
  const point = chartSeries.value[0]?.data[dataPointIndex]
  if (!point) return

  const timestamp = new Date(point.x)
  const HOUR = 60 * 60 * 1000
  const DAY = 24 * HOUR
  const WEEK = 7 * DAY

  let start: Date, end: Date

  switch (timeFrame.value) {
    case 'hour':
      start = timestamp
      end = new Date(timestamp.getTime() + HOUR)
      break
    case 'day':
      start = new Date(timestamp.setHours(0, 0, 0, 0))
      end = new Date(new Date(start).setHours(23, 59, 59, 999))
      break
    case 'week':
      start = timestamp
      end = new Date(timestamp.getTime() + WEEK)
      break
    case 'month':
      start = new Date(timestamp.getFullYear(), timestamp.getMonth(), 1)
      end = new Date(timestamp.getFullYear(), timestamp.getMonth() + 1, 0, 23, 59, 59, 999)
      break
    default:
      start = timestamp
      end = new Date(timestamp.getTime() + HOUR)
  }

  setDateRange(start, end)
}

function handleReset() {
  const newFilters = { ...urlState.filters.value }
  delete (newFilters as Record<string, unknown>).start_date
  delete (newFilters as Record<string, unknown>).end_date
  newFilters.date_preset = 'last_24_hours'
  urlState.filters.value = newFilters
  chartRef.value?.resetSeries()
}

const formattedTotal = computed(() => {
  if (totalAlerts.value >= 1000000) return `${(totalAlerts.value / 1000000).toFixed(1)}M`
  if (totalAlerts.value >= 1000) return `${(totalAlerts.value / 1000).toFixed(1)}K`
  return totalAlerts.value.toLocaleString()
})
</script>

<template>
  <Card class="!py-3 !gap-2">
    <CardContent class="!px-4">
      <div class="flex items-center justify-between mb-2">
        <h3 class="text-sm font-medium text-muted-foreground">Alert Activity</h3>
        <div class="flex items-center gap-2">
          <button
            v-if="hasCustomDateRange"
            type="button"
            class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-muted-foreground hover:text-foreground bg-muted/50 hover:bg-muted rounded-md transition-colors"
            title="Reset to last 24 hours"
            @click="handleReset"
          >
            <Icon name="lucide:rotate-ccw" class="size-3" />
            Reset
          </button>
          <span v-if="!pending && totalAlerts > 0" class="text-xs text-muted-foreground tabular-nums">
            {{ formattedTotal }} alerts
          </span>
        </div>
      </div>

      <apexchart
        v-if="chartSeries[0]?.data.length"
        ref="chart"
        type="bar"
        :height="chartHeight"
        :options="chartOptions"
        :series="chartSeries"
      />
      <div v-else-if="pending" class="flex items-center justify-center" :style="{ height: `${chartHeight}px` }">
        <Icon name="lucide:loader-2" class="size-5 animate-spin text-muted-foreground" />
      </div>
      <div v-else class="flex items-center justify-center text-sm text-muted-foreground" :style="{ height: `${chartHeight}px` }">
        No alert data for selected period
      </div>

      <p v-if="!isMobile" class="text-xs text-muted-foreground mt-2 text-center">
        {{ hasCustomDateRange ? 'Custom range selected' : 'Click bar to filter, drag to select range' }}
      </p>
    </CardContent>
  </Card>
</template>

<style scoped>
:deep(.apexcharts-tooltip) {
  border: 1px solid var(--color-border) !important;
  background: var(--color-popover) !important;
  box-shadow: var(--shadow-lg);
  border-radius: var(--radius-md) !important;
}

:deep(.apexcharts-tooltip-title) {
  padding: 6px 10px !important;
  background: var(--color-muted) !important;
  border-bottom: 1px solid var(--color-border) !important;
  font-weight: 500;
}

:deep(.apexcharts-tooltip-series-group) {
  padding: 4px 10px !important;
}

:deep(.apexcharts-bar-area) {
  cursor: pointer;
}

:deep(.apexcharts-zoomable) {
  cursor: crosshair !important;
}
</style>

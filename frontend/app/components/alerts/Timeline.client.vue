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
import { getActivePresetId } from '@/utils/datePresets'
import {
  getTimelineBucketDuration,
  getTimelineBucketDisplayRange,
  getTimelineColumnWidth,
  getTimelineXAxisRange,
} from '@/utils/timelineChart'

interface ChartInstance {
  updateOptions(options: ApexOptions, redrawPaths?: boolean, animate?: boolean): Promise<void>
  resetSeries(): void
  destroy(): void
}

// Accept urlState from parent to ensure single source of truth
// This eliminates race conditions when both Table and Timeline update URL state
const props = defineProps<{
  urlState: ReturnType<typeof useNavigableUrlState>
}>()

const urlState = props.urlState

const colorMode = useColorMode()
const { width } = useWindowSize()

const {
  pending,
  chartSeries,
  totalAlerts,
  timeFrame,
  dateRange,
} = useTimelineData(urlState)

const rangeDurationHours = computed(() =>
  (dateRange.value.end.getTime() - dateRange.value.start.getTime()) / (1000 * 60 * 60)
)

const hasCustomDateRange = computed(() => {
  const filters = urlState.filters.value
  return !!(filters.start_date && filters.end_date && !getActivePresetId(filters))
})

const dynamicXAxisRange = computed(() => {
  const data = chartSeries.value[0]?.data ?? []
  const fullStart = dateRange.value.start.getTime()
  const fullEnd = dateRange.value.end.getTime()

  return getTimelineXAxisRange(data.map(point => point.x), fullStart, fullEnd, timeFrame.value)
})

const dynamicColumnWidth = computed(() => {
  const data = chartSeries.value[0]?.data ?? []
  const point = data[0]
  if (!point) return 12
  return getTimelineColumnWidth(
    data.map(item => item.x),
    getTimelineBucketDuration(point.bucketStart, timeFrame.value),
  )
})

const chartRef = useTemplateRef<ChartInstance>('chart')

// Prevent ApexCharts memory leaks - destroy chart instance on unmount
onBeforeUnmount(() => {
  chartRef.value?.destroy()
})

const isMobile = computed(() => width.value < 768)
const chartHeight = computed(() => isMobile.value ? 140 : 180)

/**
 * Calculate optimal tick count for x-axis based on data density.
 */
const dynamicTickAmount = computed(() => {
  const pointCount = chartSeries.value[0]?.data?.length ?? 0
  const chartWidth = isMobile.value ? 300 : 600 // Approximate

  if (timeFrame.value === 'minute') return isMobile.value ? 4 : 6

  // For very few points, limit ticks to avoid cluttered labels
  if (pointCount <= 2) return 3
  if (pointCount <= 5) return Math.min(pointCount + 1, 5)
  if (pointCount <= 10) return 6

  // For more points, calculate based on available width (~80px per label)
  return Math.min(Math.floor(chartWidth / 80), 12)
})

const xAxisLabelFormat = computed<string>(() => {
  switch (timeFrame.value) {
    case 'minute':
      return 'HH:mm'
    case 'hour':
      return rangeDurationHours.value > 24 ? 'dd MMM HH:mm' : 'HH:mm'
    case 'day':
      return 'dd MMM'
    case 'week':
      return 'dd MMM'
    case 'month':
      return 'MMM yy'
    default:
      return 'HH:mm'
  }
})

const tooltipDateTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
})
const tooltipTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  hour: '2-digit',
  minute: '2-digit',
})
const tooltipDateFormatter = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})
const tooltipMonthFormatter = new Intl.DateTimeFormat('en-GB', {
  month: 'short',
  year: 'numeric',
})

function formatTooltipBucketRange(bucketStart: number): string {
  const { start, end } = getTimelineBucketDisplayRange(
    bucketStart,
    dateRange.value.start.getTime(),
    dateRange.value.end.getTime(),
    timeFrame.value,
  )

  if (timeFrame.value === 'minute') {
    return tooltipDateTimeFormatter.format(start)
  }

  if (timeFrame.value === 'hour') {
    const startDate = tooltipDateFormatter.format(start)
    const endDate = tooltipDateFormatter.format(end)
    const formattedEnd = startDate === endDate
      ? tooltipTimeFormatter.format(end)
      : tooltipDateTimeFormatter.format(end)
    return `${tooltipDateTimeFormatter.format(start)}–${formattedEnd}`
  }

  if (timeFrame.value === 'month') {
    const formattedStart = tooltipMonthFormatter.format(start)
    const formattedEnd = tooltipMonthFormatter.format(end)
    return formattedStart === formattedEnd ? formattedStart : `${formattedStart}–${formattedEnd}`
  }

  const formattedStart = tooltipDateFormatter.format(start)
  const formattedEnd = tooltipDateFormatter.format(end)
  return formattedStart === formattedEnd ? formattedStart : `${formattedStart}–${formattedEnd}`
}

// Chart color from design system (--chart-1 changes between light/dark)
const chartColor = ref(getChartColor(1))

// Update chart color when theme changes
watch(() => colorMode.value, () => {
  nextTick(() => {
    chartColor.value = getChartColor(1)
  })
})

// Only override what's unique to this chart - rest comes from window.Apex
const chartOptions = computed(() => ({
  chart: {
    id: 'alerts-timeline',
    background: 'transparent',
    animations: {
      enabled: true,
      easing: 'easeout',
      dynamicAnimation: {
        enabled: true,
        speed: 300, // Fast smooth transition on data updates
      },
    },
    zoom: {
      enabled: !isMobile.value,
      type: 'x',
      autoScaleYaxis: true,
      allowMouseWheelZoom: false,
    },
    events: {
      zoomed: handleZoomed,
      dataPointSelection: handleBarClick,
    },
  },
  plotOptions: {
    bar: { borderRadius: 3, columnWidth: dynamicColumnWidth.value },
  },
  xaxis: {
    type: 'datetime',
    min: dynamicXAxisRange.value.min,
    max: dynamicXAxisRange.value.max,
    tickAmount: dynamicTickAmount.value,
    labels: {
      datetimeUTC: false,
      format: xAxisLabelFormat.value,
      rotate: -45,
      rotateAlways: false,
      hideOverlappingLabels: true,
      style: {
        fontSize: '11px',
      },
    },
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
    // apexcharts 5.13+ defaults tooltip.arrow to true; keep the prior flush look
    arrow: false,
    x: {
      formatter: (value, opts) => {
        const point = opts
          ? chartSeries.value[opts.seriesIndex]?.data[opts.dataPointIndex]
          : undefined
        return formatTooltipBucketRange(point?.bucketStart ?? Number(value))
      },
    },
    y: { formatter: (val: number) => `${val} alert${val !== 1 ? 's' : ''}` },
  },
  colors: [chartColor.value],
}) as ApexOptions)

/** Update URL filters with new date range, clearing any preset */
function setDateRange(start: Date, end: Date) {
  const newFilters = { ...urlState.filters.value }
  delete (newFilters as Record<string, unknown>).date_preset
  newFilters.start_date = start.toISOString()
  newFilters.end_date = end.toISOString()
  urlState.filters.value = newFilters
}

const debouncedSetDateRange = useDebounceFn(setDateRange, 300)

function handleZoomed(_: unknown, { xaxis }: { xaxis: { min?: number; max?: number } }) {
  if (xaxis.min !== undefined && xaxis.max !== undefined && xaxis.max > xaxis.min) {
    debouncedSetDateRange(new Date(xaxis.min), new Date(xaxis.max))
  }
}

function handleBarClick(_: unknown, __: unknown, { dataPointIndex }: { dataPointIndex: number }) {
  const point = chartSeries.value[0]?.data[dataPointIndex]
  if (!point) return

  const timestamp = new Date(point.bucketStart)
  const MINUTE = 60 * 1000
  const HOUR = 60 * 60 * 1000
  const DAY = 24 * HOUR
  const WEEK = 7 * DAY

  let start: Date, end: Date

  switch (timeFrame.value) {
    case 'minute':
      start = timestamp
      end = new Date(timestamp.getTime() + MINUTE - 1)
      break
    case 'hour':
      start = timestamp
      end = new Date(timestamp.getTime() + HOUR - 1)
      break
    case 'day': {
      const dayStart = new Date(timestamp)
      dayStart.setHours(0, 0, 0, 0)
      const dayEnd = new Date(dayStart)
      dayEnd.setHours(23, 59, 59, 999)
      start = dayStart
      end = dayEnd
      break
    }
    case 'week':
      start = timestamp
      end = new Date(timestamp.getTime() + WEEK - 1)
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
  newFilters.date_preset = 'last-24-hours'
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

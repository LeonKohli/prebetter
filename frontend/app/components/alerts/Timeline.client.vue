<script setup lang="ts">
/**
 * AlertsTimeline.client.vue - Interactive bar chart showing alert volume over time
 *
 * Features:
 * - Click on bar to filter table to that time period
 * - Drag to zoom/select a time range
 * - Outliers: the axis stops below a burst, which is marked with its real count
 * - Custom reset button
 *
 * The bucketing, the axis cap and the Apex options live in utils/timelineChart*.ts, where they
 * are tested; this component wires them to the URL state.
 * Most styling comes from window.Apex in apexcharts.client.ts plugin.
 */
import type { ApexOptions } from 'apexcharts'
import { useDebounceFn } from '@vueuse/core'
import { getActivePresetId } from '@/utils/datePresets'
import { createTimelineOptions, createTimelineSeries } from '@/utils/timelineChartOptions'

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

const {
  pending,
  model,
  totalAlerts,
  timeFrame,
  dateRange,
} = useTimelineData(urlState)

const hasCustomDateRange = computed(() => {
  const filters = urlState.filters.value
  return !!(filters.start_date && filters.end_date && !getActivePresetId(filters))
})

const chartRef = useTemplateRef<ChartInstance>('chart')

// Prevent ApexCharts memory leaks - destroy chart instance on unmount
onBeforeUnmount(() => {
  chartRef.value?.destroy()
})

// Chart color from design system (--chart-1 changes between light/dark)
const chartColor = ref(getChartColor(1))

// Update chart color when theme changes
watch(() => colorMode.value, () => {
  return nextTick(() => {
    chartColor.value = getChartColor(1)
  })
})

/** Update URL filters with new date range, clearing any preset */
function setDateRange(start: Date, end: Date) {
  const newFilters = { ...urlState.filters.value }
  delete (newFilters as Record<string, unknown>).date_preset
  newFilters.start_date = start.toISOString()
  newFilters.end_date = end.toISOString()
  urlState.filters.value = newFilters
}

const debouncedSetDateRange = useDebounceFn(setDateRange, 300)

function handleZoomed(_chart: unknown, options?: { xaxis: { min: number, max: number } }) {
  const xaxis = options?.xaxis
  if (xaxis && xaxis.max > xaxis.min) {
    debouncedSetDateRange(new Date(xaxis.min), new Date(xaxis.max))
      .catch(err => console.error('Failed to update timeline range:', err))
  }
}

// A bar filters to exactly the bucket it counted: the same calendar (the viewer's zone) the server used.
function handleBarClick(_event: unknown, _chart: unknown, options?: { dataPointIndex: number }) {
  const bar = options ? model.value.bars[options.dataPointIndex] : undefined
  if (bar) setDateRange(new Date(bar.bucketStart), new Date(bar.bucketEnd - 1))
}

function handleReset() {
  const newFilters = { ...urlState.filters.value }
  delete (newFilters as Record<string, unknown>).start_date
  delete (newFilters as Record<string, unknown>).end_date
  newFilters.date_preset = 'last-24-hours'
  urlState.filters.value = newFilters
  chartRef.value?.resetSeries()
}

const series = computed(() => createTimelineSeries(model.value, chartColor.value))

const chartOptions = computed(() => createTimelineOptions({
  model: model.value,
  frame: timeFrame.value,
  color: chartColor.value,
  mode: colorMode.value === 'dark' ? 'dark' : 'light',
  window: { start: dateRange.value.start.getTime(), end: dateRange.value.end.getTime() },
  onZoomed: handleZoomed,
  onBarClick: handleBarClick,
}))

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
        v-if="model.bars.length"
        ref="chart"
        type="bar"
        :height="180"
        :options="chartOptions"
        :series="series"
      />
      <div v-else-if="pending" class="flex h-[180px] items-center justify-center max-md:h-[140px]">
        <Icon name="lucide:loader-2" class="size-5 animate-spin text-muted-foreground" />
      </div>
      <div v-else class="flex h-[180px] items-center justify-center text-sm text-muted-foreground max-md:h-[140px]">
        No alert data for selected period
      </div>

      <p v-if="model.capped" class="mt-2 text-center text-xs text-muted-foreground">
        Axis stops at {{ model.yMax?.toLocaleString('en-GB') }}; ▲ marks a bar above it with its real count.
      </p>
      <p class="mt-2 hidden text-center text-xs text-muted-foreground md:block">
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

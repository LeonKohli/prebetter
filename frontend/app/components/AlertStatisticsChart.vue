<script setup lang="ts">
import { LineChart } from '@/components/ui/chart-line'

interface TimelineDataPoint {
  timestamp: string
  count: number
}

interface TimelineResponse {
  time_frame: string
  start_date: string
  end_date: string
  data: TimelineDataPoint[]
}

const props = defineProps<{
  timeRange?: number
  timeFrame?: 'hour' | 'day' | 'week' | 'month'
  severity?: string
  classification?: string
  analyzerName?: string
}>()

const loading = ref(true)
const error = ref<string | null>(null)
const timelineData = ref<TimelineResponse | null>(null)

// Transform the data for the line chart
const chartData = computed(() => {
  if (!timelineData.value) return []
  
  return timelineData.value.data.map(point => ({
    label: new Date(point.timestamp).toLocaleString(),
    value: point.count
  }))
})

const fetchTimeline = async () => {
  try {
    loading.value = true
    error.value = null
    
    // Calculate start and end dates based on timeRange
    const end = new Date()
    const start = new Date(end.getTime() - (props.timeRange || 24) * 60 * 60 * 1000)
    
    const response = await $fetch<TimelineResponse>('/api/timeline', {
      params: {
        time_frame: props.timeFrame || 'hour',
        start_date: start.toISOString(),
        end_date: end.toISOString(),
        severity: props.severity,
        classification: props.classification,
        analyzer_name: props.analyzerName
      },
      onResponseError({ response }) {
        throw new Error(response._data?.detail || 'Failed to load timeline data')
      }
    })
    
    timelineData.value = response
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load timeline data'
    console.error('Error fetching timeline:', err)
  } finally {
    loading.value = false
  }
}

// Fetch data when component mounts or when props change
watch(
  [
    () => props.timeRange,
    () => props.timeFrame,
    () => props.severity,
    () => props.classification,
    () => props.analyzerName
  ],
  fetchTimeline,
  { immediate: true }
)

// Refresh data periodically
const refreshInterval = 5 * 60 * 1000 // 5 minutes
let refreshTimer: NodeJS.Timeout

onMounted(() => {
  refreshTimer = setInterval(fetchTimeline, refreshInterval)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<template>
  <div class="w-full space-y-4">
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-medium">Alert Timeline (Last {{ props.timeRange || 24 }} hours)</h3>
      <Button
        v-if="error"
        variant="ghost"
        size="sm"
        @click="fetchTimeline"
      >
        <Icon name="lucide:refresh-cw" class="w-4 h-4 mr-2" />
        Retry
      </Button>
    </div>

    <div class="relative min-h-[200px] w-full">
      <!-- Loading State -->
      <div
        v-if="loading"
        class="absolute inset-0 flex items-center justify-center bg-background/50 backdrop-blur-sm"
      >
        <Spinner class="w-6 h-6" />
      </div>

      <!-- Error State -->
      <div
        v-else-if="error"
        class="absolute inset-0 flex items-center justify-center text-destructive"
      >
        <p>{{ error }}</p>
      </div>

      <!-- Chart -->
      <template v-else-if="timelineData">
        <LineChart
          :data="chartData"
          index="label"
          :categories="['value']"
          :y-formatter="(tick) => typeof tick === 'number' ? tick.toString() : ''"
          :show-grid-line="false"
          :show-legend="false"
          class="h-[200px] w-full"
        />
      </template>
    </div>
  </div>
</template>
<template>
  <div class="p-4 md:p-6 space-y-6">
    <!-- Toolbar - matches AlertsToolbar pattern -->
    <div class="flex items-center justify-between pb-2">
      <div class="flex items-center gap-3">
        <Select :model-value="String(days)" @update:model-value="handleDaysChange">
          <SelectTrigger class="h-8 w-[130px] text-xs font-medium">
            <SelectValue :placeholder="`${days} days`" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1">Last 24 hours</SelectItem>
            <SelectItem value="3">Last 3 days</SelectItem>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="14">Last 14 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div class="flex items-center gap-2">
        <!-- Live/Pause Toggle with Connection Status -->
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                variant="outline"
                size="sm"
                class="h-8 px-3 text-xs font-medium"
                @click="toggleLive"
              >
                <!-- Paused: user disabled live mode -->
                <template v-if="!isLive">
                  <Icon name="lucide:pause" class="mr-2 size-4 text-muted-foreground" />
                  Paused
                </template>
                <!-- Live + Connected: green pulsing dot -->
                <template v-else-if="sseStatus === 'OPEN'">
                  <span class="mr-2 size-2 rounded-full bg-green-500 animate-pulse" />
                  Live
                </template>
                <!-- Live + Connecting: yellow spinner -->
                <template v-else-if="sseStatus === 'CONNECTING'">
                  <Icon name="lucide:loader-2" class="mr-2 size-4 text-yellow-500 animate-spin" />
                  Connecting
                </template>
                <!-- Live + Closed/Error: red dot -->
                <template v-else>
                  <span class="mr-2 size-2 rounded-full bg-red-500" />
                  Offline
                </template>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom" :side-offset="4">
              <template v-if="!isLive">
                Click to enable real-time updates
              </template>
              <template v-else-if="sseStatus === 'OPEN'">
                Connected - receiving live updates
              </template>
              <template v-else-if="sseStatus === 'CONNECTING'">
                Establishing connection...
              </template>
              <template v-else-if="sseError">
                Connection error - will retry automatically
              </template>
              <template v-else>
                Disconnected - will retry automatically
              </template>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>

    <HeartbeatSummaryGrid
      :total-nodes="totalNodes"
      :total-agents="totalAgents"
      :summary="statusSummaryList"
      :last-updated="lastUpdatedAt"
    />

    <HeartbeatNodeList
      :nodes="nodes"
      :total-agents="totalAgents"
      @agent-select="handleAgentSelect"
    />

    <HeartbeatTimelineTable
      title="Recent heartbeats"
      :items="timelineItems"
      :pending="timelinePending"
      :error="timelineErrorNormalized"
      :pagination="timelinePagination"
      @update:page="timelineSetPage"
    />
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  requiresAuth: true,
})

useSeoMeta({
  title: 'Heartbeat Monitor - Prebetter IDS',
  description: 'Visual heartbeat monitoring for analyzer agents and nodes.',
})

const router = useRouter()

const {
  nodes,
  totalNodes,
  totalAgents,
  statusSummaryList,
  refresh: refreshStatus,
  days,
  setDays,
  lastUpdated,
} = useHeartbeatStatus({ autoRefreshMs: 0 }) // SSE handles refresh, disable polling

const {
  items: timelineItems,
  pending: timelinePending,
  error: timelineError,
  pagination: timelinePagination,
  setPage: setTimelinePage,
  refresh: refreshTimeline,
  setHours: setTimelineHours,
} = useHeartbeatTimeline({ hours: 24, pageSize: 50 })

// Sync timeline hours when lookback days change (days * 24 = hours)
watch(days, (newDays) => {
  setTimelineHours(newDays * 24)
}, { immediate: true })

// Live mode state - controls whether real-time updates are active
const isLive = ref(true)

// SSE refresh handler - refresh both status and timeline
async function performSseRefresh() {
  if (!isLive.value) return // Skip if paused
  await Promise.all([
    refreshStatus(),
    refreshTimeline(),
  ])
}

// Initialize SSE stream for real-time heartbeat updates
// VueUse's useEventSource is SSR-safe - it checks isClient internally
const {
  status: sseStatus,
  error: sseError,
  close: sseClose,
  open: sseOpen,
} = useHeartbeatStream({
  onNewHeartbeats: performSseRefresh,
  debounceMs: 2000,
})

// Toggle live mode - pauses/resumes SSE stream
function toggleLive() {
  isLive.value = !isLive.value

  if (isLive.value) {
    // Resume: reopen SSE and refresh data
    sseOpen()
    refreshStatus()
    refreshTimeline()
  } else {
    // Pause: close SSE connection
    sseClose()
  }
}

const lastUpdatedAt = computed(() => lastUpdated.value)
const timelineErrorNormalized = computed(() => timelineError.value ?? null)

function handleAgentSelect(payload: { node: string; agent: string }) {
  router.push({
    path: `/heartbeats/${encodeURIComponent(payload.node)}/${encodeURIComponent(payload.agent)}`,
  })
}

function handleDaysChange(value: unknown) {
  if (value == null) return
  setDays(Number(value))
}

function timelineSetPage(value: number) {
  setTimelinePage(value)
}
</script>

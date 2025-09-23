<template>
  <div class="p-4 md:p-6 space-y-6">
    <div class="flex flex-wrap items-center gap-3">
      <Button variant="ghost" size="sm" as-child>
        <NuxtLink to="/heartbeats" class="flex items-center gap-2">
          <Icon name="lucide:chevron-left" class="size-4" />
          Back to overview
        </NuxtLink>
      </Button>
      <div class="text-sm text-muted-foreground">
        {{ decodedNode }}
        <Icon name="lucide:chevron-right" class="mx-1 inline size-4 align-middle text-muted-foreground/70" aria-hidden="true" />
        {{ decodedAgent }}
      </div>
    </div>

    <Card>
      <CardHeader class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <CardTitle class="text-xl font-semibold">{{ decodedAgent }}</CardTitle>
          <CardDescription>Node {{ decodedNode }}</CardDescription>
        </div>
        <HeartbeatStatusBadge v-if="agentInfo" :status="agentInfo.status" />
      </CardHeader>
      <CardContent>
        <template v-if="statusPending">
          <div class="flex items-center gap-2 text-sm text-muted-foreground">
            <Icon name="lucide:loader-2" class="size-4 animate-spin" />
            Loading agent details…
          </div>
        </template>
        <template v-else-if="!agentInfo">
          <Alert variant="destructive">
            <Icon name="lucide:alert-triangle" class="size-4" />
            <AlertTitle>Agent not found</AlertTitle>
            <AlertDescription>
              We could not find recent heartbeats for this agent within the selected window. Try expanding the lookback range or verify the agent is still reporting.
            </AlertDescription>
          </Alert>
        </template>
        <template v-else>
          <dl class="grid gap-4 sm:grid-cols-2">
            <div>
              <dt class="text-xs uppercase tracking-wide text-muted-foreground">Status</dt>
              <dd class="mt-1 text-sm">
                <HeartbeatStatusBadge :status="agentInfo.status" />
              </dd>
            </div>
            <div>
              <dt class="text-xs uppercase tracking-wide text-muted-foreground">Last heartbeat</dt>
              <dd class="mt-1 text-sm">
                {{ relativeLastHeartbeat }}
                <span v-if="agentInfo.latest_heartbeat_at" class="block text-xs text-muted-foreground mt-0.5">
                  {{ formatAbsolute(agentInfo.latest_heartbeat_at) }}
                </span>
              </dd>
            </div>
            <div>
              <dt class="text-xs uppercase tracking-wide text-muted-foreground">Heartbeat interval</dt>
              <dd class="mt-1 text-sm">
                <span v-if="agentInfo.heartbeat_interval">Every {{ agentInfo.heartbeat_interval }} seconds</span>
                <span v-else class="italic text-muted-foreground">Not supplied</span>
              </dd>
            </div>
            <div>
              <dt class="text-xs uppercase tracking-wide text-muted-foreground">Metadata</dt>
              <dd class="mt-1 text-sm text-muted-foreground">
                {{ agentInfo.model || 'Unknown model' }}
                <span v-if="agentInfo.version">· v{{ agentInfo.version }}</span>
                <span v-if="agentInfo.class">· {{ agentInfo.class }}</span>
              </dd>
            </div>
          </dl>
        </template>
      </CardContent>
      <CardFooter class="flex flex-wrap items-center gap-3 border-t border-border/70 py-4">
        <div class="flex items-center gap-2 text-sm">
          <span class="text-muted-foreground">Status lookback</span>
          <Select :model-value="String(days)" @update:model-value="handleDaysChange">
            <SelectTrigger class="h-8 w-[120px] text-xs">
              <SelectValue :placeholder="`${days}`" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">24 hours</SelectItem>
              <SelectItem value="3">3 days</SelectItem>
              <SelectItem value="7">7 days</SelectItem>
              <SelectItem value="14">14 days</SelectItem>
              <SelectItem value="30">30 days</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="flex items-center gap-2 text-sm">
          <span class="text-muted-foreground">Auto refresh</span>
          <Switch :checked="autoRefreshEnabled" @update:checked="updateAutoRefresh" />
        </div>
        <Button
          variant="outline"
          size="sm"
          :disabled="statusPending"
          @click="refreshStatus"
          class="flex items-center gap-2"
        >
          <Icon :name="statusPending ? 'lucide:loader-2' : 'lucide:refresh-cw'" class="size-4" :class="{ 'animate-spin': statusPending }" />
          Refresh
        </Button>
      </CardFooter>
    </Card>

    <HeartbeatTimelineTable
      title="Agent timeline"
      :subtitle="`Recent heartbeats for ${decodedAgent}`"
      :items="filteredTimelineItems"
      :pending="timelinePending"
      :error="timelineErrorNormalized"
      :pagination="timelinePagination"
      :show-host="false"
      empty-message="No heartbeat entries for this agent in the selected window."
      @update:page="setTimelinePage"
    >
      <template #actions>
        <div class="flex items-center gap-2 text-sm">
          <span class="text-muted-foreground">Timeline window</span>
          <Select :model-value="String(timelineHours)" @update:model-value="handleTimelineHoursChange">
            <SelectTrigger class="h-8 w-[120px] text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="12">12 hours</SelectItem>
              <SelectItem value="24">24 hours</SelectItem>
              <SelectItem value="48">48 hours</SelectItem>
              <SelectItem value="72">72 hours</SelectItem>
              <SelectItem value="168">7 days</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </template>
    </HeartbeatTimelineTable>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from '#imports'
import HeartbeatStatusBadge from '@/components/heartbeats/HeartbeatStatusBadge.vue'
import HeartbeatTimelineTable from '@/components/heartbeats/HeartbeatTimelineTable.vue'
import { useHeartbeatStatus, useHeartbeatTimeline, formatRelativeFromSeconds } from '@/composables/useHeartbeats'
import { formatTimestamp } from '@/utils/timestampFormatter'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

definePageMeta({
  requiresAuth: true,
})

const route = useRoute()
const decodedNode = computed(() => decodeURIComponent(route.params.node as string))
const decodedAgent = computed(() => decodeURIComponent(route.params.agent as string))

useSeoMeta({
  title: () => `Heartbeat · ${decodedAgent.value} on ${decodedNode.value}`,
  description: 'Detailed heartbeat timeline for a single analyzer agent.',
})

const {
  nodes,
  pending: statusPending,
  refresh: refreshStatus,
  days,
  setDays,
  autoRefreshEnabled,
} = useHeartbeatStatus({ autoRefreshMs: 60_000 })

const {
  items: timelineItems,
  pending: timelinePending,
  error: timelineError,
  pagination: timelinePagination,
  hours: timelineHours,
  setHours,
  setPage: setTimelinePage,
} = useHeartbeatTimeline({ hours: 48, pageSize: 100 })

const timelineErrorNormalized = computed(() => timelineError.value ?? null)

const agentInfo = computed(() => {
  const node = nodes.value.find((candidate) => candidate.name === decodedNode.value)
  return node?.agents.find((candidate) => candidate.name === decodedAgent.value)
})

const relativeLastHeartbeat = computed(() =>
  agentInfo.value ? formatRelativeFromSeconds(agentInfo.value.seconds_ago) : 'No heartbeat received yet'
)

const filteredTimelineItems = computed(() =>
  timelineItems.value.filter(
    (item) => item.host_name === decodedNode.value && item.analyzer_name === decodedAgent.value,
  )
)

function handleDaysChange(value: unknown) {
  if (value == null) return
  setDays(Number(value))
}

function handleTimelineHoursChange(value: unknown) {
  if (value == null) return
  setHours(Number(value))
}

function formatAbsolute(value: string) {
  // Use centralized formatter with UTC display
  return formatTimestamp(value, { style: 'short' })
}

function updateAutoRefresh(value: boolean) {
  autoRefreshEnabled.value = value
}
</script>

<template>
  <div class="p-4 md:p-6 space-y-6">
    <header class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Heartbeat Monitor</h1>
        <p class="text-sm text-muted-foreground max-w-2xl">
          Monitor analyzer heartbeats across every node. Use the filters to locate agents that are late or offline and drill into their detailed timeline.
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <ClientOnly>
          <Button
            variant="outline"
            size="sm"
            :disabled="statusPending"
            @click="refreshStatus"
            class="flex items-center gap-2"
          >
            <Icon
              :name="statusPending ? 'lucide:loader-2' : 'lucide:refresh-cw'"
              class="size-4"
              :class="{ 'animate-spin': statusPending }"
            />
            Refresh
          </Button>
          <template #fallback>
            <Button variant="outline" size="sm" class="flex items-center gap-2" disabled>
              <Icon name="lucide:refresh-cw" class="size-4" />
              Refresh
            </Button>
          </template>
        </ClientOnly>

        <div class="flex items-center gap-2 text-sm">
          <span class="text-muted-foreground">Lookback</span>
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
          <Switch
            :checked="autoRefreshEnabled"
            @update:checked="updateAutoRefresh"
          />
          <Select :model-value="String(autoRefreshInterval)" @update:model-value="handleIntervalChange">
            <SelectTrigger class="h-8 w-[110px] text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="15000">15 seconds</SelectItem>
              <SelectItem value="30000">30 seconds</SelectItem>
              <SelectItem value="60000">60 seconds</SelectItem>
              <SelectItem value="120000">2 minutes</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </header>

    <HeartbeatSummaryGrid
      :total-nodes="totalNodes"
      :total-agents="totalAgents"
      :summary="statusSummaryList"
      :last-updated="lastUpdatedAt"
    />

    <section class="space-y-3">
      <header class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex flex-wrap items-center gap-3">
          <div class="flex items-center gap-2 text-sm">
            <span class="text-muted-foreground">Filter status</span>
            <Select :model-value="statusFilter" @update:model-value="handleStatusFilterChange">
              <SelectTrigger class="h-8 w-[140px] text-xs">
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem v-for="option in statusOptions" :key="option" :value="option">
                  {{ option.charAt(0).toUpperCase() + option.slice(1) }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="relative">
            <Icon name="lucide:search" class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              v-model="searchTerm"
              placeholder="Search nodes or agents"
              class="h-9 w-[220px] pl-9"
              type="search"
            />
          </div>
        </div>
        <div class="text-xs text-muted-foreground">
          Showing {{ filteredAgentCount }} of {{ totalAgents }} agents
        </div>
      </header>

      <HeartbeatNodeList
        :nodes="filteredNodes"
        :total-agents="filteredAgentCount"
        @agent-select="handleAgentSelect"
      />
    </section>

    <HeartbeatTimelineTable
      title="Recent heartbeats"
      subtitle="Latest heartbeats within the selected window"
      :items="timelineItems"
      :pending="timelinePending"
      :error="timelineErrorNormalized"
      :pagination="timelinePagination"
      @update:page="timelineSetPage"
    >
      <template #actions>
        <div class="flex items-center gap-2 text-sm">
          <span class="text-muted-foreground">Window</span>
          <Select :model-value="String(timelineHours)" @update:model-value="handleHoursChange">
            <SelectTrigger class="h-8 w-[110px] text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="6">6 hours</SelectItem>
              <SelectItem value="12">12 hours</SelectItem>
              <SelectItem value="24">24 hours</SelectItem>
              <SelectItem value="48">48 hours</SelectItem>
              <SelectItem value="72">72 hours</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </template>
    </HeartbeatTimelineTable>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from '#imports'
import { useHeartbeatStatus, useHeartbeatTimeline } from '@/composables/useHeartbeats'
import HeartbeatSummaryGrid from '@/components/heartbeats/HeartbeatSummaryGrid.vue'
import HeartbeatNodeList from '@/components/heartbeats/HeartbeatNodeList.vue'
import HeartbeatTimelineTable from '@/components/heartbeats/HeartbeatTimelineTable.vue'
import type { HeartbeatNode } from '@/types/heartbeats'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'

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
  pending: statusPending,
  refresh: refreshStatus,
  days,
  setDays,
  lastUpdated,
  autoRefreshEnabled,
  autoRefreshInterval,
} = useHeartbeatStatus({ autoRefreshMs: 60_000 })

const {
  items: timelineItems,
  pending: timelinePending,
  error: timelineError,
  pagination: timelinePagination,
  hours: timelineHours,
  setHours: setTimelineHours,
  setPage: setTimelinePage,
} = useHeartbeatTimeline({ hours: 24, pageSize: 50 })

const searchTerm = ref('')
const statusFilter = ref<StatusFilter>('all')
const lastUpdatedAt = computed(() => lastUpdated.value)
const timelineErrorNormalized = computed(() => timelineError.value ?? null)

const statusOptions = computed(() => {
  const options = new Set<string>()
  statusSummaryList.value.forEach((item) => options.add(item.status))
  return Array.from(options)
})

type StatusFilter = 'all' | string

const filteredNodes = computed<HeartbeatNode[]>(() => {
  const term = searchTerm.value.trim().toLowerCase()
  return nodes.value
    .map((node) => {
      const filteredAgents = node.agents.filter((agent) => {
        const matchesStatus = statusFilter.value === 'all' || agent.status === statusFilter.value
        if (!matchesStatus) return false

        if (!term) return true
        return (
          node.name.toLowerCase().includes(term) ||
          agent.name.toLowerCase().includes(term) ||
          (agent.model?.toLowerCase().includes(term) ?? false) ||
          (agent.version?.toLowerCase().includes(term) ?? false)
        )
      })

      if (filteredAgents.length === 0) {
        return null
      }

      return {
        ...node,
        agents: filteredAgents,
      }
    })
    .filter((value): value is HeartbeatNode => Boolean(value))
})

const filteredAgentCount = computed(() =>
  filteredNodes.value.reduce((total, node) => total + node.agents.length, 0)
)

function handleAgentSelect(payload: { node: string; agent: string }) {
  router.push({
    path: `/heartbeats/${encodeURIComponent(payload.node)}/${encodeURIComponent(payload.agent)}`,
  })
}

function handleDaysChange(value: unknown) {
  if (value == null) return
  setDays(Number(value))
}

function handleIntervalChange(value: unknown) {
  if (value == null) return
  autoRefreshInterval.value = Number(value)
}

function handleHoursChange(value: unknown) {
  if (value == null) return
  setTimelineHours(Number(value))
}

function timelineSetPage(value: number) {
  setTimelinePage(value)
}

function updateAutoRefresh(value: boolean) {
  autoRefreshEnabled.value = value
}

function handleStatusFilterChange(value: unknown) {
  const next = value == null ? 'all' : String(value)
  statusFilter.value = next as StatusFilter
}
</script>

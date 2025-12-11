<template>
  <section aria-labelledby="heartbeat-summary-heading" class="space-y-2">
    <div class="flex items-center justify-between gap-2">
      <div>
        <h2 id="heartbeat-summary-heading" class="font-display text-lg font-semibold">Heartbeat Overview</h2>
        <p class="text-sm text-muted-foreground">
          Snapshot of connected nodes and analyzer agents.
        </p>
      </div>
      <div class="font-mono text-xs text-muted-foreground whitespace-nowrap" data-allow-mismatch="children">
        <span v-if="lastUpdated">Updated {{ formatTimestamp(lastUpdated, { style: 'short', showTimezone: true }) }}</span>
      </div>
    </div>

    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <!-- Static cards: Total Nodes & Total Agents -->
      <Card v-for="card in staticCards" :key="card.label">
        <CardHeader class="space-y-1">
          <template v-if="pending">
            <Skeleton class="h-4 w-24" />
            <Skeleton class="h-8 w-16" />
          </template>
          <template v-else>
            <CardTitle class="text-sm font-medium text-muted-foreground">{{ card.label }}</CardTitle>
            <div class="font-mono text-3xl font-semibold tabular-nums">{{ card.value }}</div>
          </template>
        </CardHeader>
      </Card>

      <!-- Dynamic status cards -->
      <Card v-for="item in displaySummary" :key="item.status" class="border-dashed">
        <CardHeader class="space-y-1">
          <template v-if="pending">
            <Skeleton class="h-4 w-20" />
            <Skeleton class="h-7 w-12" />
          </template>
          <template v-else>
            <HeartbeatStatusBadge :status="item.status" />
            <div class="font-mono text-2xl font-semibold tabular-nums">{{ item.count }}</div>
          </template>
        </CardHeader>
      </Card>
    </div>
  </section>
</template>

<script setup lang="ts">
import { formatTimestamp } from '@/utils/timestampFormatter'

type SummaryItem = { status: string; count: number }

interface Props {
  totalNodes: number
  totalAgents: number
  summary: SummaryItem[]
  lastUpdated: Date | null
  pending?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  summary: () => [],
  lastUpdated: null,
  pending: false,
})

const staticCards = computed(() => [
  { label: 'Total Nodes', value: props.totalNodes },
  { label: 'Total Agents', value: props.totalAgents },
])

// Show 4 placeholder cards when loading, actual summary when loaded
const displaySummary = computed(() =>
  props.pending
    ? [{ status: 'active', count: 0 }, { status: 'inactive', count: 0 }, { status: 'offline', count: 0 }, { status: 'unknown', count: 0 }]
    : props.summary
)
</script>

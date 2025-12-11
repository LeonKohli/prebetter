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

    <!-- Loading skeleton -->
    <div v-if="pending" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Card v-for="i in 6" :key="`skeleton-${i}`">
        <CardHeader class="space-y-2">
          <Skeleton class="h-4 w-24" />
          <Skeleton class="h-8 w-16" />
        </CardHeader>
      </Card>
    </div>

    <!-- Loaded content -->
    <div v-else class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Card>
        <CardHeader class="space-y-1">
          <CardTitle class="text-sm font-medium text-muted-foreground">Total Nodes</CardTitle>
          <div class="font-mono text-3xl font-semibold tabular-nums">{{ totalNodes }}</div>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader class="space-y-1">
          <CardTitle class="text-sm font-medium text-muted-foreground">Total Agents</CardTitle>
          <div class="font-mono text-3xl font-semibold tabular-nums">{{ totalAgents }}</div>
        </CardHeader>
      </Card>

      <Card
        v-for="item in summary"
        :key="item.status"
        class="border-dashed"
      >
        <CardHeader class="space-y-1">
          <HeartbeatStatusBadge :status="item.status" />
          <div class="font-mono text-2xl font-semibold tabular-nums">{{ item.count }}</div>
        </CardHeader>
      </Card>
    </div>
  </section>
</template>

<script setup lang="ts">
import { formatTimestamp } from '@/utils/timestampFormatter'

type SummaryItem = {
  status: string
  count: number
}

interface Props {
  totalNodes: number
  totalAgents: number
  summary: SummaryItem[]
  lastUpdated: Date | null
  pending?: boolean
}

withDefaults(defineProps<Props>(), {
  summary: () => [],
  lastUpdated: null,
  pending: false,
})
</script>

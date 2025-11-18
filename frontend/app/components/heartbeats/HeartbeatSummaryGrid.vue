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
import type { PropType } from 'vue'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import HeartbeatStatusBadge from '@/components/heartbeats/HeartbeatStatusBadge.vue'
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
}

withDefaults(defineProps<Props>(), {
  summary: () => [],
  lastUpdated: null,
})
</script>

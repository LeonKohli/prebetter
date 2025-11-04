<template>
  <section aria-labelledby="heartbeat-nodes-heading" class="space-y-4">
    <header class="flex items-center justify-between">
      <div>
        <h2 id="heartbeat-nodes-heading" class="text-lg font-semibold">Nodes &amp; Agents</h2>
        <p class="text-sm text-muted-foreground">Click an agent to view its heartbeat timeline and metadata.</p>
      </div>
      <div class="text-sm text-muted-foreground">
        {{ totalAgents }} agents across {{ nodes.length }} nodes
      </div>
    </header>

    <div v-if="nodes.length === 0" class="border border-dashed rounded-md p-6 text-center text-sm text-muted-foreground">
      No agents match the current filters.
    </div>

    <Card
      v-for="node in nodes"
      :key="node.name"
      class="border-border/60"
    >
      <CardHeader class="pb-3">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle class="text-base font-semibold">{{ node.name }}</CardTitle>
            <CardDescription v-if="node.os" class="text-xs text-muted-foreground">{{ node.os }}</CardDescription>
          </div>
          <Badge variant="outline" class="text-xs">
            {{ node.agents.length }} {{ node.agents.length === 1 ? 'agent' : 'agents' }}
          </Badge>
        </div>
      </CardHeader>

      <CardContent class="px-0">
        <Table class="table-fixed">
          <TableHeader>
            <TableRow>
              <TableHead class="w-[35%]">Agent</TableHead>
              <TableHead class="w-[20%]">Status</TableHead>
              <TableHead class="w-[20%]">Last heartbeat</TableHead>
              <TableHead class="w-[15%]">Interval</TableHead>
              <TableHead class="w-[10%] text-right">&nbsp;</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="agent in node.agents"
              :key="agent.name"
              class="cursor-pointer transition hover:bg-muted/40 focus-visible:bg-muted/60 outline-none"
              role="button"
              tabindex="0"
              @click="handleSelect(node.name, agent.name)"
              @keydown.enter.prevent="handleSelect(node.name, agent.name)"
              @keydown.space.prevent="handleSelect(node.name, agent.name)"
            >
              <TableCell class="align-middle">
                <div class="flex flex-col">
                  <span class="font-medium">{{ agent.name }}</span>
                  <span class="text-xs text-muted-foreground">
                    {{ agent.model || 'Unknown model' }}
                    <span v-if="agent.version">· v{{ agent.version }}</span>
                    <span v-if="agent.class">· {{ agent.class }}</span>
                  </span>
                </div>
              </TableCell>
              <TableCell class="align-middle">
                <HeartbeatStatusBadge :status="agent.status" />
              </TableCell>
              <TableCell class="align-middle text-sm">
                {{ formatRelativeFromSeconds(agent.seconds_ago) }}
                <span v-if="agent.latest_heartbeat_at" class="block text-[11px] text-muted-foreground">
                  {{ formatAbsolute(agent.latest_heartbeat_at) }}
                </span>
              </TableCell>
              <TableCell class="align-middle text-sm text-muted-foreground">
                <span v-if="agent.heartbeat_interval">
                  {{ agent.heartbeat_interval }}s
                </span>
                <span v-else class="italic">n/a</span>
              </TableCell>
              <TableCell class="align-middle text-right pr-4">
                <Icon name="lucide:arrow-up-right" class="size-4 text-muted-foreground" aria-hidden="true" />
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  </section>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type { HeartbeatNode } from '@/types/heartbeats'
import HeartbeatStatusBadge from '@/components/heartbeats/HeartbeatStatusBadge.vue'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatRelativeFromSeconds } from '@/composables/useHeartbeats'
import { formatTimestamp } from '@/utils/timestampFormatter'

const props = defineProps({
  nodes: {
    type: Array as PropType<HeartbeatNode[]>,
    default: () => [],
  },
  totalAgents: {
    type: Number,
    default: 0,
  },
})

const emit = defineEmits<{
  (e: 'agent-select', payload: { node: string; agent: string }): void
}>()

function handleSelect(node: string, agent: string) {
  emit('agent-select', { node, agent })
}

function formatAbsolute(value: string) {
  // Use centralized formatter with local timezone display
  return formatTimestamp(value, { style: 'short' })
}
</script>

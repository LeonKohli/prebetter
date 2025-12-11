<template>
  <section aria-labelledby="heartbeat-nodes-heading" class="space-y-4">
    <header class="flex items-center justify-between">
      <div>
        <h2 id="heartbeat-nodes-heading" class="font-display text-lg font-semibold">Nodes &amp; Agents</h2>
        <p class="text-sm text-muted-foreground">Click an agent to view its heartbeat timeline and metadata.</p>
      </div>
      <div v-if="!pending" class="text-sm text-muted-foreground">
        {{ totalAgents }} agents across {{ nodes.length }} nodes
      </div>
    </header>

    <!-- Loading skeleton -->
    <template v-if="pending">
      <Card v-for="i in 3" :key="`skeleton-node-${i}`" class="border-border/60">
        <CardHeader class="pb-3">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="space-y-1">
              <Skeleton class="h-5 w-32" />
              <Skeleton class="h-3 w-24" />
            </div>
            <Skeleton class="h-5 w-16" />
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
              <TableRow v-for="j in 3" :key="`skeleton-agent-${i}-${j}`">
                <TableCell>
                  <div class="space-y-1">
                    <Skeleton class="h-4 w-28" />
                    <Skeleton class="h-3 w-36" />
                  </div>
                </TableCell>
                <TableCell><Skeleton class="h-5 w-16" /></TableCell>
                <TableCell>
                  <div class="space-y-1">
                    <Skeleton class="h-4 w-20" />
                    <Skeleton class="h-3 w-24" />
                  </div>
                </TableCell>
                <TableCell><Skeleton class="h-4 w-10" /></TableCell>
                <TableCell class="text-right"><Skeleton class="h-4 w-4 ml-auto" /></TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </template>

    <!-- Empty state -->
    <div v-else-if="nodes.length === 0" class="border border-dashed rounded-md p-6 text-center text-sm text-muted-foreground">
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
import { formatRelativeFromSeconds } from '@/composables/useHeartbeats'

const props = withDefaults(defineProps<{
  nodes?: HeartbeatNode[]
  totalAgents?: number
  pending?: boolean
}>(), {
  nodes: () => [],
  totalAgents: 0,
  pending: false,
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

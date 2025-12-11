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

    <!-- Loading skeleton - reuse same card structure with skeleton content -->
    <template v-if="pending">
      <HeartbeatNodeCard v-for="i in 3" :key="`skeleton-${i}`" skeleton />
    </template>

    <!-- Empty state -->
    <div v-else-if="nodes.length === 0" class="border border-dashed rounded-md p-6 text-center text-sm text-muted-foreground">
      No agents match the current filters.
    </div>

    <!-- Loaded nodes -->
    <HeartbeatNodeCard
      v-else
      v-for="node in nodes"
      :key="node.name"
      :node="node"
      @select="handleSelect"
    />
  </section>
</template>

<script setup lang="ts">
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
  agentSelect: [payload: { node: string; agent: string }]
}>()

function handleSelect(node: string, agent: string) {
  emit('agentSelect', { node, agent })
}
</script>

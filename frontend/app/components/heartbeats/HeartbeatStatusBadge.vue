<template>
  <span
    class="inline-flex items-center gap-2 text-sm font-medium leading-none"
    :class="{ 'text-muted-foreground': meta.isMuted }"
    :title="meta.description"
  >
    <span
      class="size-2.5 rounded-full border border-border shadow-[0_0_0_1.5px_rgba(0,0,0,0.05)]"
      :style="{ backgroundColor: meta.color }
      "
      aria-hidden="true"
    />
    <span class="capitalize">{{ meta.label }}</span>
  </span>
</template>

<script setup lang="ts">
interface Props {
  status: HeartbeatStatus
}

const props = defineProps<Props>()

const STATUS_META: Record<string, { label: string; color: string; description: string; isMuted?: boolean }> = {
  active: {
    label: 'active',
    color: 'oklch(0.72 0.18 145)',
    description: 'Agent is sending heartbeats within the configured interval.',
  },
  inactive: {
    label: 'inactive',
    color: 'oklch(0.76 0.11 78)',
    description: 'Agent is late but still within the offline grace window.',
  },
  offline: {
    label: 'offline',
    color: 'var(--destructive)',
    description: 'Agent has missed heartbeats beyond the grace period.',
  },
  unknown: {
    label: 'unknown',
    color: 'oklch(0.68 0.02 250)',
    description: 'Heartbeat status could not be determined.',
    isMuted: true,
  },
}

const meta = computed(() => {
  const statusKey = (props.status || 'unknown').toLowerCase()
  return (
    STATUS_META[statusKey] || {
      label: statusKey,
      color: 'oklch(0.68 0.02 250)',
      description: 'Custom heartbeat status returned by the server.',
      isMuted: true,
    }
  )
})
</script>

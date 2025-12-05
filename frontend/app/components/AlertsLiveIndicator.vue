<template>
  <ClientOnly>
    <div class="flex items-center gap-2">
      <!-- Connection status indicator -->
      <div
        class="flex items-center gap-1.5 text-xs"
        :class="statusClasses"
      >
        <span
          class="size-2 rounded-full"
          :class="dotClasses"
        />
        <span class="font-medium">{{ statusText }}</span>
      </div>

      <!-- New alerts badge with refresh button -->
      <Button
        v-if="newAlertCount > 0"
        variant="secondary"
        size="sm"
        class="h-7 gap-1.5 px-2 text-xs animate-in fade-in"
        @click="handleRefresh"
      >
        <Icon name="lucide:bell" class="size-3.5" />
        {{ newAlertCount }} new
        <Icon name="lucide:refresh-cw" class="size-3" />
      </Button>
    </div>

    <template #fallback>
      <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
        <span class="size-2 rounded-full bg-muted-foreground/50" />
        <span class="font-medium">Connecting...</span>
      </div>
    </template>
  </ClientOnly>
</template>

<script setup lang="ts">
const emit = defineEmits<{
  refresh: []
}>()

const { isConnected, isConnecting, newAlertCount, clearAlerts } = useAlertStream()

const statusText = computed(() => {
  if (isConnecting.value) return 'Connecting...'
  if (isConnected.value) return 'Live'
  return 'Disconnected'
})

const statusClasses = computed(() => {
  if (isConnected.value) return 'text-green-600 dark:text-green-400'
  if (isConnecting.value) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-muted-foreground'
})

const dotClasses = computed(() => {
  if (isConnected.value) return 'bg-green-500 animate-pulse'
  if (isConnecting.value) return 'bg-yellow-500 animate-pulse'
  return 'bg-muted-foreground'
})

function handleRefresh() {
  clearAlerts()
  emit('refresh')
}
</script>

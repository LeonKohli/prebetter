<template>
  <Transition name="slide-up">
    <!-- Outer: Fixed positioning + flexbox centering (no transforms) -->
    <div
      v-if="selectionCount > 0"
      class="fixed inset-x-0 bottom-16 z-50 flex justify-center px-4"
    >
      <!-- Inner: The actual selection bar (animates with translateY only) -->
      <div
        class="flex items-center gap-4 px-6 py-3
               bg-card border border-border rounded-lg shadow-lg
               max-w-2xl w-full"
        role="toolbar"
        aria-label="Bulk actions for selected alerts"
      >
        <!-- Clear selection -->
        <Button
          variant="ghost"
          size="sm"
          @click="clearSelection"
          class="h-8 w-8 p-0 shrink-0"
          aria-label="Clear selection"
        >
          <Icon name="lucide:x" class="h-4 w-4" />
        </Button>

        <!-- Selection indicator -->
        <div class="flex items-center gap-2 shrink-0">
          <div class="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10">
            <Icon name="lucide:check-square" class="h-4 w-4 text-primary" />
          </div>
          <div class="flex flex-col">
            <span class="text-sm font-semibold leading-none">
              {{ selectionCount }} {{ selectionCount === 1 ? 'alert' : 'alerts' }}
            </span>
            <span class="text-xs text-muted-foreground leading-none mt-0.5">
              Selected
            </span>
          </div>
        </div>

        <!-- Divider -->
        <div class="h-8 w-px bg-border shrink-0" />

        <!-- Actions -->
        <div class="flex items-center gap-2 ml-auto">
          <!-- Export (future feature) -->
          <Button
            variant="outline"
            size="sm"
            @click="handleExport"
            class="h-8 px-3 text-xs font-medium"
            disabled
            title="Export feature coming soon"
          >
            <Icon name="lucide:download" class="mr-2 h-3.5 w-3.5" />
            Export
          </Button>

          <!-- Delete -->
          <Button
            variant="destructive"
            size="sm"
            @click="handleBulkDelete"
            class="h-8 px-3 text-xs font-medium"
            :disabled="pending"
          >
            <Icon name="lucide:trash-2" class="mr-2 h-3.5 w-3.5" />
            Delete
          </Button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { useAlertTableContext } from '@/composables/useAlertTableContext'

interface Emits {
  bulkDelete: []
  export: []
}

const emit = defineEmits<Emits>()

const { table, pending } = useAlertTableContext()

// Computed selection count
const selectionCount = computed(() => table.getSelectedRowModel().rows.length)

// Clear all selected rows
const clearSelection = () => {
  table.resetRowSelection()
}

// Handle bulk delete
const handleBulkDelete = () => {
  emit('bulkDelete')
}

// Handle export (future feature)
const handleExport = () => {
  emit('export')
}

// Keyboard shortcut: ESC to clear selection
if (process.client) {
  useEventListener(document, 'keydown', (e: KeyboardEvent) => {
    if (e.key === 'Escape' && selectionCount.value > 0) {
      clearSelection()
    }
  })
}
</script>

<style scoped>
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease-out;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(3rem);
}
</style>

<script setup lang="ts">
import type { FetchError } from 'ofetch'

type DeleteState =
  | { mode: 'single'; alert: AlertListItem }
  | { mode: 'bulk'; alerts: AlertListItem[] }
  | { mode: 'grouped'; sourceIp: string; targetIp: string; totalCount: number }

interface DeleteResponse {
  deleted: number
  rows: number
}

const props = defineProps<{
  open: boolean
  state: DeleteState | null
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  'deleted': []
}>()

const pending = ref(false)
const error = ref<string | null>(null)

const dialogOpen = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value)
})

const actionLabel = computed(() => {
  if (!props.state) return 'Delete'
  if (props.state.mode === 'single') return 'Delete alert'
  if (props.state.mode === 'bulk') return `Delete ${props.state.alerts.length} alert${props.state.alerts.length === 1 ? '' : 's'}`
  return 'Delete group'
})

// Reset error when dialog opens
watch(() => props.open, (isOpen) => {
  if (isOpen) error.value = null
})

async function confirmDeletion() {
  if (!props.state) return

  pending.value = true
  error.value = null

  try {
    if (props.state.mode === 'grouped') {
      await $fetch<DeleteResponse>('/api/alerts', {
        method: 'DELETE',
        query: {
          source_ip: props.state.sourceIp,
          target_ip: props.state.targetIp,
        },
      })
    } else {
      const ids = props.state.mode === 'single'
        ? [props.state.alert.id]
        : props.state.alerts.map((alert) => alert.id)

      await $fetch<DeleteResponse>('/api/alerts', {
        method: 'DELETE',
        query: {
          ids: ids.join(','),
        },
      })
    }

    emit('update:open', false)
    emit('deleted')
  } catch (err) {
    const fetchError = err as FetchError & { data?: { detail?: string } }
    error.value = fetchError?.data?.detail || fetchError?.message || 'Failed to delete alerts.'
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <AlertDialog v-model:open="dialogOpen">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle class="flex items-center gap-2">
          <Icon name="lucide:trash-2" class="h-5 w-5 text-destructive" />
          <template v-if="state?.mode === 'grouped'">
            Delete Grouped Alerts
          </template>
          <template v-else-if="state?.mode === 'bulk'">
            Delete Selected Alerts
          </template>
          <template v-else>
            Delete Alert
          </template>
        </AlertDialogTitle>
        <AlertDialogDescription>
          This action cannot be undone. This will permanently delete the alert data from the Prelude database.
        </AlertDialogDescription>
      </AlertDialogHeader>

      <!-- Single Alert Details -->
      <div v-if="state?.mode === 'single'" class="rounded-lg border bg-muted/50 p-4">
        <dl class="space-y-3 text-sm">
          <div class="flex items-start justify-between gap-4">
            <dt class="text-xs font-medium text-muted-foreground">Alert ID</dt>
            <dd class="font-mono text-sm">#{{ state.alert.id }}</dd>
          </div>
          <div v-if="state.alert.classification_text" class="flex items-start justify-between gap-4">
            <dt class="text-xs font-medium text-muted-foreground">Classification</dt>
            <dd class="text-right text-sm break-words max-w-[60%]">
              {{ state.alert.classification_text }}
            </dd>
          </div>
          <div class="flex items-start justify-between gap-4">
            <dt class="text-xs font-medium text-muted-foreground">Source</dt>
            <dd class="font-mono text-xs">{{ state.alert.source_ipv4 || '—' }}</dd>
          </div>
          <div class="flex items-start justify-between gap-4">
            <dt class="text-xs font-medium text-muted-foreground">Target</dt>
            <dd class="font-mono text-xs">{{ state.alert.target_ipv4 || '—' }}</dd>
          </div>
        </dl>
      </div>

      <!-- Bulk Selection Info -->
      <div v-else-if="state?.mode === 'bulk'" class="rounded-lg border bg-muted/50 p-4">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-destructive/10">
            <Icon name="lucide:layers" class="h-5 w-5 text-destructive" />
          </div>
          <div class="flex-1 space-y-1">
            <p class="text-sm font-medium">
              {{ state.alerts.length }} alert{{ state.alerts.length === 1 ? '' : 's' }} selected
            </p>
            <p class="text-xs text-muted-foreground">
              All related records will be permanently removed
            </p>
          </div>
        </div>
      </div>

      <!-- Grouped Alerts Info -->
      <div v-else-if="state?.mode === 'grouped'" class="rounded-lg border bg-muted/50 p-4">
        <div class="space-y-4">
          <div class="flex items-center gap-3">
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-destructive/10">
              <Icon name="lucide:network" class="h-5 w-5 text-destructive" />
            </div>
            <div class="flex-1 space-y-1">
              <p class="text-sm font-medium">IP Pair Group</p>
              <p class="text-xs text-muted-foreground">
                {{ state.totalCount }} alert{{ state.totalCount === 1 ? '' : 's' }} affected
              </p>
            </div>
          </div>
          <dl class="space-y-2 text-sm border-t pt-3">
            <div class="flex items-center justify-between gap-4">
              <dt class="text-xs font-medium text-muted-foreground">Source IP</dt>
              <dd class="font-mono text-xs">{{ state.sourceIp }}</dd>
            </div>
            <div class="flex items-center justify-between gap-4">
              <dt class="text-xs font-medium text-muted-foreground">Target IP</dt>
              <dd class="font-mono text-xs">{{ state.targetIp }}</dd>
            </div>
          </dl>
        </div>
      </div>

      <!-- Error Display -->
      <div v-if="error" class="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-3">
        <Icon name="lucide:alert-circle" class="h-4 w-4 shrink-0 text-destructive" />
        <p class="text-sm text-destructive">{{ error }}</p>
      </div>

      <AlertDialogFooter>
        <AlertDialogCancel as-child>
          <Button variant="outline" :disabled="pending">
            Cancel
          </Button>
        </AlertDialogCancel>
        <AlertDialogAction as-child>
          <Button variant="destructive" :disabled="pending" @click="confirmDeletion">
            <Icon v-if="pending" name="lucide:loader-2" class="mr-2 h-4 w-4 animate-spin" />
            {{ actionLabel }}
          </Button>
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>

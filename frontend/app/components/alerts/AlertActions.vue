<script setup lang="ts">
import type { AlertListItem, FlattenedGroupedAlert, CompactGroupedAlert } from '@/types/alerts'

const props = defineProps<{
  alert: AlertListItem | FlattenedGroupedAlert | CompactGroupedAlert
  isGrouped: boolean
}>()

const emit = defineEmits<{
  viewDetails: [alertId: string]
}>()

function copyId() {
  let id = ''
  if (props.isGrouped) {
    // For grouped rows, use the IP pair as identifier (works for both legacy and compact)
    const anyAlert = props.alert as any
    const src = anyAlert?.source_ipv4 || 'unknown'
    const dst = anyAlert?.target_ipv4 || 'unknown'
    id = `${src}-${dst}`
  } else if ('id' in props.alert) {
    id = props.alert.id
  }
  navigator.clipboard.writeText(id || '')
}

function handleViewDetails() {
  // For ungrouped view, use the alert ID directly
  if (!props.isGrouped && 'id' in props.alert) {
    emit('viewDetails', props.alert.id)
  }
}
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button variant="ghost" class="h-8 w-8 p-0">
        <span class="sr-only">Open menu</span>
        <Icon name="lucide:more-horizontal" class="h-4 w-4" />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end">
      <DropdownMenuLabel>Actions</DropdownMenuLabel>
      <DropdownMenuItem v-if="!isGrouped" @click="handleViewDetails">
        <Icon name="lucide:file-text" class="mr-2 h-4 w-4" />
        View details
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem @click="copyId">
        <Icon name="lucide:copy" class="mr-2 h-4 w-4" />
        Copy {{ isGrouped ? 'IP pair' : 'alert ID' }}
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>

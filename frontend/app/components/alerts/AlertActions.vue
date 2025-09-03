<script setup lang="ts">
import { MoreHorizontal } from 'lucide-vue-next'
import type { AlertListItem, FlattenedGroupedAlert } from '@/types/alerts'

const props = defineProps<{
  alert: AlertListItem | FlattenedGroupedAlert
  isGrouped: boolean
}>()

const emit = defineEmits<{
  viewDetails: [alertId: string]
}>()

function copyId() {
  const id = props.isGrouped 
    ? `${(props.alert as FlattenedGroupedAlert).source_ipv4}-${(props.alert as FlattenedGroupedAlert).target_ipv4}` 
    : (props.alert as AlertListItem).id
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
        <MoreHorizontal class="h-4 w-4" />
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
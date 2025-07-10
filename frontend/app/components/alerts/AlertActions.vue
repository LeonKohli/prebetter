<script setup lang="ts">
import { MoreHorizontal } from 'lucide-vue-next'

const props = defineProps<{
  alert: any
  isGrouped: boolean
}>()

function copyId() {
  const id = props.isGrouped 
    ? `${props.alert.source_ipv4}-${props.alert.target_ipv4}` 
    : props.alert.id
  navigator.clipboard.writeText(id || '')
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
      <DropdownMenuItem v-if="!isGrouped" @click="$emit('viewDetails', alert.id)">
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
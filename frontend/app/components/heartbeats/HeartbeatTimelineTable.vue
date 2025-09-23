<template>
  <Card>
    <CardHeader class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div>
        <CardTitle class="text-base font-semibold">{{ title }}</CardTitle>
        <CardDescription v-if="subtitle">{{ subtitle }}</CardDescription>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <slot name="actions" />
      </div>
    </CardHeader>

    <CardContent class="px-0">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead v-if="showHost">Node</TableHead>
            <TableHead>Agent</TableHead>
            <TableHead>Timestamp</TableHead>
            <TableHead>Model</TableHead>
            <TableHead>Version</TableHead>
            <TableHead>Class</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-if="pending">
            <TableCell :colspan="showHost ? 6 : 5" class="py-12 text-center text-sm text-muted-foreground">
              <div class="flex items-center justify-center gap-2">
                <Icon name="lucide:loader-2" class="size-4 animate-spin" />
                Loading timeline…
              </div>
            </TableCell>
          </TableRow>
          <TableRow v-else-if="error">
            <TableCell :colspan="showHost ? 6 : 5" class="py-12 text-center text-sm text-destructive">
              Failed to load timeline. {{ error.message || 'Please try again.' }}
            </TableCell>
          </TableRow>
          <TableRow v-else-if="items.length === 0">
            <TableCell :colspan="showHost ? 6 : 5" class="py-12 text-center text-sm text-muted-foreground">
              {{ emptyMessage }}
            </TableCell>
          </TableRow>
          <TableRow v-else v-for="item in items" :key="itemKey(item)">
            <TableCell v-if="showHost" class="align-middle font-medium">{{ item.host_name }}</TableCell>
            <TableCell class="align-middle">{{ item.analyzer_name }}</TableCell>
            <TableCell class="align-middle text-sm">
              {{ formatAbsolute(item.timestamp) }}
            </TableCell>
            <TableCell class="align-middle text-sm text-muted-foreground">{{ item.model || '—' }}</TableCell>
            <TableCell class="align-middle text-sm text-muted-foreground">{{ item.version || '—' }}</TableCell>
            <TableCell class="align-middle text-sm text-muted-foreground">{{ item.class_ || '—' }}</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </CardContent>

    <CardFooter v-if="pagination.pages > 1" class="flex flex-col gap-3 border-t border-border/80 py-4 md:flex-row md:items-center md:justify-between">
      <div class="text-sm text-muted-foreground">
        Page {{ pagination.page }} of {{ pagination.pages }} · {{ pagination.total }} total entries
      </div>
      <div class="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          :disabled="pagination.page <= 1 || pending"
          @click="$emit('update:page', pagination.page - 1)"
        >
          <Icon name="lucide:chevron-left" class="mr-1 size-4" /> Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          :disabled="pagination.page >= pagination.pages || pending"
          @click="$emit('update:page', pagination.page + 1)"
        >
          Next <Icon name="lucide:chevron-right" class="ml-1 size-4" />
        </Button>
      </div>
    </CardFooter>
  </Card>
</template>

<script setup lang="ts">
import type { HeartbeatTimelineItem } from '@/types/heartbeats'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { formatTimestamp } from '@/utils/timestampFormatter'

interface Props {
  title: string
  subtitle?: string
  items: HeartbeatTimelineItem[]
  pending: boolean
  error?: Error | null
  pagination: {
    total: number
    page: number
    size: number
    pages: number
  }
  emptyMessage?: string
  showHost?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  subtitle: undefined,
  emptyMessage: 'No timeline data found for this period.',
  showHost: true,
})

function formatAbsolute(value: string) {
  // Use centralized formatter with UTC display
  return formatTimestamp(value, { style: 'short' })
}

function itemKey(item: HeartbeatTimelineItem) {
  return `${item.host_name}-${item.analyzer_name}-${item.timestamp}`
}
</script>

<template>
  <Card class="border-border/60">
    <CardHeader class="pb-3">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="space-y-1">
          <template v-if="skeleton">
            <Skeleton class="h-5 w-32" />
            <Skeleton class="h-3 w-24" />
          </template>
          <template v-else>
            <CardTitle class="text-base font-semibold">{{ node!.name }}</CardTitle>
            <CardDescription v-if="node!.os" class="text-xs text-muted-foreground">{{ node!.os }}</CardDescription>
          </template>
        </div>
        <Skeleton v-if="skeleton" class="h-5 w-16" />
        <Badge v-else variant="outline" class="text-xs">
          {{ node!.agents.length }} {{ node!.agents.length === 1 ? 'agent' : 'agents' }}
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
          <!-- Skeleton rows -->
          <template v-if="skeleton">
            <TableRow v-for="i in 3" :key="`skeleton-row-${i}`">
              <TableCell><Skeleton class="h-4 w-28" /><Skeleton class="h-3 w-36 mt-1" /></TableCell>
              <TableCell><Skeleton class="h-5 w-16" /></TableCell>
              <TableCell><Skeleton class="h-4 w-20" /><Skeleton class="h-3 w-24 mt-1" /></TableCell>
              <TableCell><Skeleton class="h-4 w-10" /></TableCell>
              <TableCell class="text-right"><Skeleton class="h-4 w-4 ml-auto" /></TableCell>
            </TableRow>
          </template>

          <!-- Real agent rows -->
          <TableRow
            v-else
            v-for="agent in node!.agents"
            :key="agent.name"
            class="cursor-pointer transition hover:bg-muted/40 focus-visible:bg-muted/60 outline-none"
            role="button"
            tabindex="0"
            @click="emit('select', node!.name, agent.name)"
            @keydown.enter.prevent="emit('select', node!.name, agent.name)"
            @keydown.space.prevent="emit('select', node!.name, agent.name)"
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
                {{ formatTimestamp(agent.latest_heartbeat_at, { style: 'short' }) }}
              </span>
            </TableCell>
            <TableCell class="align-middle text-sm text-muted-foreground">
              <span v-if="agent.heartbeat_interval">{{ agent.heartbeat_interval }}s</span>
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
</template>

<script setup lang="ts">
import { formatRelativeFromSeconds } from '@/composables/useHeartbeats'
import { formatTimestamp } from '@/utils/timestampFormatter'

const props = defineProps<{
  node?: HeartbeatNode
  skeleton?: boolean
}>()

const emit = defineEmits<{
  select: [node: string, agent: string]
}>()
</script>

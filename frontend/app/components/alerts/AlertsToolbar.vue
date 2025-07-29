<template>
  <div class="flex items-center justify-between pb-2">
    <div class="flex items-center gap-3">
      <div class="relative">
        <Icon name="lucide:search" class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          class="h-9 w-72 pl-9 pr-3 border-border bg-background/50 focus:bg-background transition-colors"
          placeholder="Filter alerts by classification..."
          :model-value="urlState.filters.value.classification_text || ''"
          @update:model-value="handleSearchFilter"
        />
      </div>
      
      <DateRangePicker
        v-model="dateRange"
        :includeTime="true"
      />
    </div>
    
    <div class="flex items-center gap-2">
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button
            variant="outline"
            size="sm"
            class="h-8 px-3 text-xs font-medium border-border hover:bg-background transition-all"
          >
            <Icon 
              :name="autoRefreshEnabled ? 'lucide:clock' : 'lucide:pause'" 
              class="mr-2 h-3.5 w-3.5"
            />
            {{ autoRefreshDisplayText }}
            <Icon name="lucide:chevron-down" class="ml-1 h-3 w-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>Auto-refresh interval</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            @click="setAutoRefresh(0)"
            :class="urlState.autoRefresh.value === 0 ? 'bg-accent' : ''"
          >
            <Icon name="lucide:pause" class="mr-2 h-4 w-4" />
            Inactive
          </DropdownMenuItem>
          <DropdownMenuItem
            @click="setAutoRefresh(30)"
            :class="urlState.autoRefresh.value === 30 ? 'bg-accent' : ''"
          >
            <Icon name="lucide:clock" class="mr-2 h-4 w-4" />
            30 seconds
          </DropdownMenuItem>
          <DropdownMenuItem
            @click="setAutoRefresh(60)"
            :class="urlState.autoRefresh.value === 60 ? 'bg-accent' : ''"
          >
            <Icon name="lucide:clock" class="mr-2 h-4 w-4" />
            1 minute
          </DropdownMenuItem>
          <DropdownMenuItem
            @click="setAutoRefresh(300)"
            :class="urlState.autoRefresh.value === 300 ? 'bg-accent' : ''"
          >
            <Icon name="lucide:clock" class="mr-2 h-4 w-4" />
            5 minutes
          </DropdownMenuItem>
          <DropdownMenuItem
            @click="setAutoRefresh(600)"
            :class="urlState.autoRefresh.value === 600 ? 'bg-accent' : ''"
          >
            <Icon name="lucide:clock" class="mr-2 h-4 w-4" />
            10 minutes
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      
      <ClientOnly>
        <Button
          variant="outline"
          size="sm"
          @click="$emit('toggleView')"
          class="h-8 px-3 text-xs font-medium border-border hover:bg-background transition-all"
          :disabled="pending"
        >
          <Users v-if="!isGrouped" class="mr-2 h-3.5 w-3.5" />
          <List v-else class="mr-2 h-3.5 w-3.5" />
          {{ isGrouped ? 'Show Individual' : 'Group by IP' }}
        </Button>
        <template #fallback>
          <Button
            variant="outline"
            size="sm"
            class="h-8 px-3 text-xs font-medium border-border hover:bg-background transition-all"
          >
            <Users v-if="!isGrouped" class="mr-2 h-3.5 w-3.5" />
            <List v-else class="mr-2 h-3.5 w-3.5" />
            {{ isGrouped ? 'Show Individual' : 'Group by IP' }}
          </Button>
        </template>
      </ClientOnly>
      
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button variant="outline" size="sm" class="h-8 px-3 text-xs font-medium border-border hover:bg-background">
            <Icon name="lucide:columns" class="mr-2 h-3.5 w-3.5" />
            Columns <Icon name="lucide:chevron-down" class="ml-1 h-3 w-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuCheckboxItem
            v-for="column in table.getAllColumns().filter((column) => column.getCanHide())"
            :key="column.id"
            class="capitalize"
            :model-value="column.getIsVisible()"
            @update:model-value="(value) => column.toggleVisibility(!!value)"
          >
            {{ column.id }}
          </DropdownMenuCheckboxItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Users, List } from 'lucide-vue-next'
import type { DropdownMenuCheckboxItemProps } from 'reka-ui'
import { useDebounceFn } from '@vueuse/core'
import { getTodayRange, getLast24HoursRange, isToday } from '@/utils/dateHelpers'
import DateRangePicker from '@/components/DateRangePicker.vue'
import { useAlertTableContext } from '@/composables/useAlertTableContext'

interface DateRangeValue {
  from: Date | undefined
  to: Date | undefined
}

interface Emits {
  toggleView: []
  startAutoRefresh: []
  stopAutoRefresh: []
}

const emit = defineEmits<Emits>()

const { urlState, table, isGrouped, pending } = useAlertTableContext()


const dateRange = computed<DateRangeValue>({
  get: () => {
    const filters = urlState.filters.value
    
    // Only show "Today" as default in the UI, don't force it into the filters
    // This allows the backend to apply its own defaults if needed
    const from = filters.start_date ? new Date(filters.start_date as string) : undefined
    const to = filters.end_date ? new Date(filters.end_date as string) : undefined
    
    // If no dates are in URL, show last 24 hours in the picker UI only
    if (!from && !to) {
      return getLast24HoursRange()
    }
    
    return { from, to }
  },
  set: (value) => {
    if (!value.from || !value.to) {
      const { start_date, end_date, ...otherFilters } = urlState.filters.value
      urlState.filters.value = otherFilters
      return
    }
    
    // Always store dates in URL to preserve them during navigation
    urlState.filters.value = {
      ...urlState.filters.value,
      start_date: value.from.toISOString(),
      end_date: value.to.toISOString()
    }
  }
})

const autoRefreshEnabled = computed(() => urlState.autoRefresh.value > 0)

const autoRefreshDisplayText = computed(() => {
  if (!autoRefreshEnabled.value) return 'Off'
  const value = urlState.autoRefresh.value
  return value >= 60 ? `${value / 60}m` : `${value}s`
})

const updateSearchFilter = (value: string | number) => {
  const stringValue = String(value)
  if (stringValue) {
    urlState.filters.value = { 
      ...urlState.filters.value, 
      classification_text: stringValue 
    }
  } else {
    const { classification_text, ...rest } = urlState.filters.value
    urlState.filters.value = rest
  }
}

const handleSearchFilter = useDebounceFn(updateSearchFilter, 300)

function setAutoRefresh(seconds: number) {
  urlState.autoRefresh.value = seconds
  if (seconds === 0) {
    emit('stopAutoRefresh')
  } else {
    emit('startAutoRefresh')
  }
}
</script>
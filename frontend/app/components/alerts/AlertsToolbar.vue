<template>
  <div class="flex items-center justify-between pb-2">
    <!-- Left side: Search filter and date range -->
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
    
    <!-- Right side: Controls -->
    <div class="flex items-center gap-2">
      <!-- Auto-refresh dropdown -->
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
      
      <!-- View toggle -->
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
      
      <!-- Column visibility dropdown -->
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button variant="outline" size="sm" class="h-8 px-3 text-xs font-medium border-border hover:bg-background">
            <Icon name="lucide:columns" class="mr-2 h-3.5 w-3.5" />
            Columns <Icon name="lucide:chevron-down" class="ml-1 h-3 w-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <template
            v-for="column in table.getAllColumns().filter((column) => column.getCanHide())"
            :key="column.id"
          >
            <DropdownMenuCheckboxItem
              v-if="columnRefs[column.id]"
              class="capitalize"
              :model-value="columnRefs[column.id]?.value"
              @update:model-value="(value) => {
                const ref = columnRefs[column.id]
                if (ref) {
                  ref.value = value
                }
              }"
            >
              {{ column.id }}
            </DropdownMenuCheckboxItem>
          </template>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Users, List } from 'lucide-vue-next'
import type { Table } from '@tanstack/vue-table'
import type { Ref } from 'vue'
import type { DropdownMenuCheckboxItemProps } from 'reka-ui'
import DateRangePicker from '@/components/DateRangePicker.vue'

interface DateRangeValue {
  from: Date | undefined
  to: Date | undefined
}

interface Props {
  urlState: any
  pending: boolean
  isGrouped: boolean
  table: Table<any>
  columnRefs: Record<string, Ref<DropdownMenuCheckboxItemProps['modelValue']>>
}

interface Emits {
  toggleView: []
  startAutoRefresh: []
  stopAutoRefresh: []
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Date range state synchronized with URL
const dateRange = computed<DateRangeValue>({
  get: () => {
    const filters = props.urlState.filters.value
    return {
      from: filters.start_date ? new Date(filters.start_date as string) : undefined,
      to: filters.end_date ? new Date(filters.end_date as string) : undefined
    }
  },
  set: (value) => {
    const currentFilters = { ...props.urlState.filters.value }
    
    if (value.from) {
      currentFilters.start_date = value.from.toISOString()
    } else {
      delete currentFilters.start_date
    }
    
    if (value.to) {
      currentFilters.end_date = value.to.toISOString()
    } else {
      delete currentFilters.end_date
    }
    
    props.urlState.filters.value = currentFilters
  }
})

// Computed properties
const autoRefreshEnabled = computed(() => props.urlState.autoRefresh.value > 0)

const autoRefreshDisplayText = computed(() => {
  if (!autoRefreshEnabled.value) return 'Off'
  const value = props.urlState.autoRefresh.value
  return value >= 60 ? `${value / 60}m` : `${value}s`
})

// Methods
function handleSearchFilter(value: string | number) {
  const stringValue = String(value)
  if (stringValue) {
    props.urlState.filters.value = { 
      ...props.urlState.filters.value, 
      classification_text: stringValue 
    }
  } else {
    const { classification_text, ...rest } = props.urlState.filters.value
    props.urlState.filters.value = rest
  }
}

function setAutoRefresh(seconds: number) {
  props.urlState.autoRefresh.value = seconds
  if (seconds === 0) {
    emit('stopAutoRefresh')
  } else {
    emit('startAutoRefresh')
  }
}
</script>
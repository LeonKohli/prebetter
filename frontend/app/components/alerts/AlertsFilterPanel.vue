<template>
  <Popover v-model:open="isOpen">
    <PopoverTrigger as-child>
      <Button
        variant="outline"
        size="sm"
        class="h-8 px-3 text-xs font-medium relative"
        :class="{ 'border-primary': activeFilterCount > 0 }"
      >
        <Icon name="lucide:sliders-horizontal" class="mr-2 size-4" />
        Filters
        <Badge
          v-if="activeFilterCount > 0"
          variant="default"
          class="ml-1.5 h-5 min-w-5 px-1.5 text-[10px]"
        >
          {{ activeFilterCount }}
        </Badge>
        <Icon name="lucide:chevron-down" class="ml-1 h-3.5 w-3.5" />
      </Button>
    </PopoverTrigger>
    <PopoverContent
      align="end"
      :side-offset="8"
      class="w-80 p-0"
    >
      <div class="p-4 pb-2">
        <div class="flex items-center justify-between">
          <h4 class="font-medium text-sm">Advanced Filters</h4>
          <Button
            v-if="activeFilterCount > 0"
            variant="ghost"
            size="sm"
            class="h-7 px-2 text-xs text-muted-foreground hover:text-destructive"
            @click="clearAllFilters"
          >
            <Icon name="lucide:x" class="mr-1 size-3" />
            Clear all
          </Button>
        </div>
      </div>

      <Separator />

      <div class="p-4 space-y-4 max-h-[400px] overflow-y-auto">
        <!-- Severity Filter -->
        <div class="space-y-2">
          <Label class="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Severity
          </Label>
          <Select
            :model-value="selectedSeverity"
            @update:model-value="handleSeverityChange"
          >
            <SelectTrigger size="sm" class="w-full">
              <SelectValue placeholder="All severities" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">
                <span class="text-muted-foreground">All severities</span>
              </SelectItem>
              <SelectSeparator />
              <SelectItem
                v-for="severity in severities"
                :key="severity"
                :value="severity"
              >
                <div class="flex items-center gap-2">
                  <span
                    class="size-2 rounded-full"
                    :class="getSeverityIndicatorClass(severity)"
                  />
                  {{ formatSeverity(severity) }}
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <!-- Analyzer Filter -->
        <div class="space-y-2">
          <Label class="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Analyzer
          </Label>
          <Select
            :model-value="selectedAnalyzer"
            @update:model-value="handleAnalyzerChange"
          >
            <SelectTrigger size="sm" class="w-full">
              <SelectValue placeholder="All analyzers" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">
                <span class="text-muted-foreground">All analyzers</span>
              </SelectItem>
              <SelectSeparator />
              <SelectItem
                v-for="analyzer in analyzers"
                :key="analyzer"
                :value="analyzer"
              >
                {{ analyzer }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Separator />

        <!-- Source IP Filter -->
        <div class="space-y-2">
          <Label class="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Source IP
          </Label>
          <InputGroup class="h-8">
            <InputGroupAddon>
              <Icon name="lucide:globe" class="size-3.5" />
            </InputGroupAddon>
            <InputGroupInput
              class="text-xs font-mono"
              placeholder="e.g. 192.168.1.100"
              :model-value="sourceIpValue"
              @update:model-value="handleSourceIpChange"
            />
            <InputGroupAddon
              v-if="sourceIpValue"
              as="button"
              type="button"
              class="cursor-pointer hover:text-foreground"
              @click="clearSourceIp"
            >
              <Icon name="lucide:x" class="size-3" />
            </InputGroupAddon>
          </InputGroup>
        </div>

        <!-- Target IP Filter -->
        <div class="space-y-2">
          <Label class="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Target IP
          </Label>
          <InputGroup class="h-8">
            <InputGroupAddon>
              <Icon name="lucide:target" class="size-3.5" />
            </InputGroupAddon>
            <InputGroupInput
              class="text-xs font-mono"
              placeholder="e.g. 10.0.0.1"
              :model-value="targetIpValue"
              @update:model-value="handleTargetIpChange"
            />
            <InputGroupAddon
              v-if="targetIpValue"
              as="button"
              type="button"
              class="cursor-pointer hover:text-foreground"
              @click="clearTargetIp"
            >
              <Icon name="lucide:x" class="size-3" />
            </InputGroupAddon>
          </InputGroup>
        </div>
      </div>

      <Separator />

      <div class="p-3 bg-muted/30">
        <p class="text-[10px] text-muted-foreground text-center">
          Filters are applied immediately
        </p>
      </div>
    </PopoverContent>
  </Popover>
</template>

<script setup lang="ts">
import type { AcceptableValue } from 'reka-ui'
import { useDebounceFn } from '@vueuse/core'
import { useAlertTableContext } from '@/composables/useAlertTableContext'
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/components/ui/input-group'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'

const { urlState } = useAlertTableContext()

const isOpen = ref(false)

// Fetch reference data for dropdowns
const { data: severitiesData } = await useFetch<string[]>('/api/reference/severities', {
  default: () => [],
  lazy: true,
})

const { data: analyzersData } = await useFetch<string[]>('/api/reference/analyzers', {
  default: () => [],
  lazy: true,
})

const severities = computed(() => severitiesData.value || [])
const analyzers = computed(() => analyzersData.value || [])

// Current filter values from URL state
const selectedSeverity = computed(() => {
  const val = urlState.filters.value.severity as string | undefined
  return val || '__all__'
})

const selectedAnalyzer = computed(() => {
  const val = urlState.filters.value.analyzer_model as string | undefined
  return val || '__all__'
})

const sourceIpValue = computed(() => {
  return (urlState.filters.value.source_ipv4 as string) || ''
})

const targetIpValue = computed(() => {
  return (urlState.filters.value.target_ipv4 as string) || ''
})

// Count active filters (excluding date filters which are shown separately)
const activeFilterCount = computed(() => {
  const filters = urlState.filters.value
  let count = 0
  if (filters.severity) count++
  if (filters.analyzer_model) count++
  if (filters.source_ipv4) count++
  if (filters.target_ipv4) count++
  return count
})

// Handlers
function handleSeverityChange(value: AcceptableValue) {
  const stringValue = value ? String(value) : '__all__'
  const newFilters = { ...urlState.filters.value }
  if (stringValue === '__all__') {
    delete newFilters.severity
  } else {
    newFilters.severity = stringValue
  }
  urlState.filters.value = newFilters
}

function handleAnalyzerChange(value: AcceptableValue) {
  const stringValue = value ? String(value) : '__all__'
  const newFilters = { ...urlState.filters.value }
  if (stringValue === '__all__') {
    delete newFilters.analyzer_model
  } else {
    newFilters.analyzer_model = stringValue
  }
  urlState.filters.value = newFilters
}

const updateSourceIp = (value: string | number) => {
  const stringValue = String(value).trim()
  const newFilters = { ...urlState.filters.value }
  if (stringValue) {
    newFilters.source_ipv4 = stringValue
  } else {
    delete newFilters.source_ipv4
  }
  urlState.filters.value = newFilters
}

const handleSourceIpChange = useDebounceFn(updateSourceIp, 400)

function clearSourceIp() {
  const { source_ipv4, ...rest } = urlState.filters.value
  urlState.filters.value = rest
}

const updateTargetIp = (value: string | number) => {
  const stringValue = String(value).trim()
  const newFilters = { ...urlState.filters.value }
  if (stringValue) {
    newFilters.target_ipv4 = stringValue
  } else {
    delete newFilters.target_ipv4
  }
  urlState.filters.value = newFilters
}

const handleTargetIpChange = useDebounceFn(updateTargetIp, 400)

function clearTargetIp() {
  const { target_ipv4, ...rest } = urlState.filters.value
  urlState.filters.value = rest
}

function clearAllFilters() {
  const {
    severity,
    analyzer_model,
    source_ipv4,
    target_ipv4,
    ...rest
  } = urlState.filters.value
  urlState.filters.value = rest
}

// Helper functions
function formatSeverity(severity: string): string {
  if (!severity) return 'Unknown'
  return severity.charAt(0).toUpperCase() + severity.slice(1).toLowerCase()
}

function getSeverityIndicatorClass(severity: string): string {
  const severityLower = severity?.toLowerCase()
  switch (severityLower) {
    case 'high':
      return 'bg-primary'
    case 'medium':
      return 'bg-amber-500'
    case 'low':
      return 'bg-muted-foreground'
    case 'info':
      return 'bg-blue-500'
    default:
      return 'bg-muted-foreground'
  }
}
</script>

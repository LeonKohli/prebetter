<template>
  <Popover v-model:open="isOpen">
    <PopoverTrigger as-child>
      <Button
        variant="outline"
        size="sm"
        class="relative -ml-px h-8 px-3 text-xs font-medium"
        :class="{ 'border-primary bg-primary/5': activeFilters.length }"
      >
        <Icon name="lucide:filter" />
        Filters
        <Badge
          v-if="activeFilters.length"
          class="absolute -top-2 -right-2 size-5 p-0"
        >
          {{ activeFilters.length }}
        </Badge>
      </Button>
    </PopoverTrigger>
    <PopoverContent align="end" class="w-80 p-0">
      <div class="flex items-center justify-between p-4">
        <span class="text-sm font-semibold">Filters</span>
        <Button
          v-if="activeFilters.length"
          variant="ghost"
          size="sm"
          @click="clearAllFilters"
        >
          <Icon name="lucide:rotate-ccw" />
          Reset all
        </Button>
      </div>

      <div v-if="activeFilters.length" class="flex flex-wrap gap-1.5 px-4 pb-4">
        <Badge
          v-for="filter in activeFilters"
          :key="filter.key"
          variant="secondary"
          as="button"
          type="button"
          class="cursor-pointer"
          @click="clearFilter(filter.key)"
        >
          <Icon v-if="filter.icon" :name="filter.icon" class="size-3" />
          <span
            v-else-if="filter.color"
            class="size-2 rounded-full"
            :class="filter.color"
          />
          {{ filter.label }}
          <Icon name="lucide:x" />
        </Badge>
      </div>

      <Separator />

      <div class="p-4 space-y-3">
        <!-- Classification Filter -->
        <div class="space-y-1.5">
          <Label class="text-xs">Classification</Label>
          <Popover v-model:open="classificationOpen">
            <PopoverTrigger as-child>
              <Button
                variant="outline"
                role="combobox"
                class="w-full justify-between font-normal"
              >
                <div class="flex items-center gap-2 truncate">
                  <Icon name="lucide:tag" class="size-4 shrink-0 text-muted-foreground" />
                  <span v-if="selectedClassifications.length === 0" class="text-muted-foreground">Any</span>
                  <span v-else-if="selectedClassifications.length === 1" class="truncate">{{ selectedClassifications[0]! }}</span>
                  <span v-else class="text-muted-foreground">{{ selectedClassifications.length }} selected</span>
                </div>
                <Icon name="lucide:chevron-down" class="size-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent class="w-72 p-0" align="start">
              <div class="flex h-9 items-center gap-2 border-b px-3">
                <Icon name="lucide:search" class="size-4 shrink-0 opacity-50" />
                <input
                  v-model="classificationSearch"
                  placeholder="Search classifications..."
                  class="placeholder:text-muted-foreground flex h-10 w-full rounded-md bg-transparent py-3 text-sm outline-none disabled:cursor-not-allowed disabled:opacity-50"
                />
              </div>
              <div v-if="classificationsStatus === 'pending'" class="py-6 text-center text-sm text-muted-foreground">
                Loading...
              </div>
              <div v-else-if="filteredClassifications.length === 0" class="py-6 text-center text-sm text-muted-foreground">
                No classification found.
              </div>
              <div v-else v-bind="containerProps" class="h-[200px] overflow-auto p-1">
                <div v-bind="wrapperProps">
                  <div
                    v-for="{ data: classification } in virtualClassifications"
                    :key="classification"
                    class="relative flex h-8 cursor-pointer select-none items-center gap-2 rounded-sm px-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground"
                    @click="toggleClassification(classification)"
                  >
                    <Checkbox
                      :model-value="selectedClassifications.includes(classification)"
                      class="pointer-events-none"
                    />
                    <span class="truncate">{{ classification }}</span>
                  </div>
                </div>
              </div>
            </PopoverContent>
          </Popover>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <!-- Severity Filter -->
          <div class="space-y-1.5">
            <Label class="text-xs">Severity</Label>
            <Popover v-model:open="severityOpen">
              <PopoverTrigger as-child>
                <Button
                  variant="outline"
                  role="combobox"
                  class="w-full justify-between font-normal"
                >
                  <div class="flex items-center gap-2 truncate">
                    <Icon name="lucide:shield-alert" class="size-4 shrink-0 text-muted-foreground" />
                    <span v-if="selectedSeverities.length === 0" class="text-muted-foreground">Any</span>
                    <span v-else-if="selectedSeverities.length === 1">{{ formatSeverity(selectedSeverities[0]!) }}</span>
                    <span v-else class="text-muted-foreground">{{ selectedSeverities.length }} selected</span>
                  </div>
                  <Icon name="lucide:chevron-down" class="size-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent class="w-48 p-0" align="start">
                <Command>
                  <CommandList>
                    <CommandGroup>
                      <CommandItem
                        v-for="severity in severitiesData"
                        :key="severity"
                        :value="severity"
                        @select="toggleSeverity(severity)"
                      >
                        <Checkbox
                          :model-value="selectedSeverities.includes(severity)"
                          class="pointer-events-none"
                        />
                        <span
                          class="size-2 rounded-full"
                          :class="getSeverityDotColor(severity)"
                        />
                        {{ formatSeverity(severity) }}
                      </CommandItem>
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          <!-- Server Filter -->
          <div class="space-y-1.5">
            <Label class="text-xs">Server</Label>
            <Popover v-model:open="serverOpen">
              <PopoverTrigger as-child>
                <Button
                  variant="outline"
                  role="combobox"
                  class="w-full justify-between font-normal"
                >
                  <div class="flex items-center gap-2 truncate">
                    <Icon name="lucide:server" class="size-4 shrink-0 text-muted-foreground" />
                    <span v-if="selectedServers.length === 0" class="text-muted-foreground">Any</span>
                    <span v-else-if="selectedServers.length === 1" class="truncate">{{ selectedServers[0]! }}</span>
                    <span v-else class="text-muted-foreground">{{ selectedServers.length }} selected</span>
                  </div>
                  <Icon name="lucide:chevron-down" class="size-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent class="w-56 p-0" align="start">
                <Command>
                  <CommandInput placeholder="Search servers..." />
                  <CommandList>
                    <CommandEmpty>No server found.</CommandEmpty>
                    <CommandGroup>
                      <CommandItem
                        v-for="server in serversData"
                        :key="server"
                        :value="server"
                        @select="toggleServer(server)"
                      >
                        <Checkbox
                          :model-value="selectedServers.includes(server)"
                          class="pointer-events-none"
                        />
                        <span class="truncate">{{ server }}</span>
                      </CommandItem>
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>
        </div>
      </div>

      <Separator />

      <div class="p-4">
        <div class="space-y-3">
          <!-- Source IP Filter -->
          <div class="space-y-1.5">
            <Label class="text-xs">Source IP</Label>
            <InputGroup>
              <InputGroupAddon>
                <Icon name="lucide:arrow-up-right" />
              </InputGroupAddon>
              <InputGroupInput
                v-model="sourceIpDraft"
                placeholder="10.0.0.1 or 10.0.0.0/24"
                class="font-mono"
                @keydown.enter="applySourceIp"
                @blur="applySourceIp"
              />
              <InputGroupAddon v-if="urlState.filters.value.source_ipv4" align="inline-end">
                <InputGroupButton size="icon-xs" @click="clearSourceIp">
                  <Icon name="lucide:x" />
                </InputGroupButton>
              </InputGroupAddon>
            </InputGroup>
            <p
              v-if="sourceIpHint"
              class="text-xs px-1"
              :class="sourceIpHint.startsWith('Matches:') ? 'text-muted-foreground' : 'text-destructive'"
            >
              {{ sourceIpHint }}
            </p>
          </div>

          <!-- Target IP Filter -->
          <div class="space-y-1.5">
            <Label class="text-xs">Target IP</Label>
            <InputGroup>
              <InputGroupAddon>
                <Icon name="lucide:arrow-down-right" />
              </InputGroupAddon>
              <InputGroupInput
                v-model="targetIpDraft"
                placeholder="10.0.0.1 or 10.0.0.0/24"
                class="font-mono"
                @keydown.enter="applyTargetIp"
                @blur="applyTargetIp"
              />
              <InputGroupAddon v-if="urlState.filters.value.target_ipv4" align="inline-end">
                <InputGroupButton size="icon-xs" @click="clearTargetIp">
                  <Icon name="lucide:x" />
                </InputGroupButton>
              </InputGroupAddon>
            </InputGroup>
            <p
              v-if="targetIpHint"
              class="text-xs px-1"
              :class="targetIpHint.startsWith('Matches:') ? 'text-muted-foreground' : 'text-destructive'"
            >
              {{ targetIpHint }}
            </p>
          </div>

        </div>
      </div>

      <Separator />

      <div class="p-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Icon name="lucide:network" class="size-4 text-muted-foreground" />
            <Label class="text-xs font-normal">Show all alerts</Label>
          </div>
          <Switch
            :model-value="!requireIps"
            @update:model-value="(v: boolean) => setRequireIps(!v)"
          />
        </div>
        <p class="text-xs text-muted-foreground mt-1.5 pl-6">
          Include alerts without IP addresses (switches to list view)
        </p>
      </div>
    </PopoverContent>
  </Popover>
</template>

<script setup lang="ts">
import { getIPFilterHint } from '~/utils/ipFilter'

const { urlState } = useAlertTableContext()

const isOpen = ref(false)
const severityOpen = ref(false)
const serverOpen = ref(false)
const classificationOpen = ref(false)

const { data: severitiesData } = useFetch<string[]>('/api/reference/severities', { default: () => [], lazy: true })
const { data: serversData } = useFetch<string[]>('/api/reference/servers', { default: () => [], lazy: true })
const { data: classificationsData, status: classificationsStatus } = useFetch<string[]>('/api/reference/classifications', { default: () => [], lazy: true })

const SEVERITY_COLORS: Record<string, string> = {
  high: 'bg-primary',
  medium: 'bg-amber-500',
  low: 'bg-muted-foreground',
  info: 'bg-blue-500',
}

function formatSeverity(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase()
}

function getSeverityDotColor(value: string) {
  return SEVERITY_COLORS[value.toLowerCase()] ?? 'bg-muted-foreground'
}

// Multi-select filters - writable computeds following dateRange pattern from AlertsToolbar
const selectedSeverities = computed({
  get: () => urlState.filters.value.severity ? String(urlState.filters.value.severity).split(',') : [],
  set: (values: string[]) => {
    const nextFilters: Record<string, string | number> = { ...urlState.filters.value }
    delete nextFilters.severity
    if (values.length) nextFilters.severity = values.join(',')
    urlState.filters.value = nextFilters
  },
})

const selectedServers = computed({
  get: () => urlState.filters.value.server ? String(urlState.filters.value.server).split(',') : [],
  set: (values: string[]) => {
    const nextFilters: Record<string, string | number> = { ...urlState.filters.value }
    delete nextFilters.server
    if (values.length) nextFilters.server = values.join(',')
    urlState.filters.value = nextFilters
  },
})

const selectedClassifications = computed({
  get: () => urlState.filters.value.classification_text ? String(urlState.filters.value.classification_text).split(',') : [],
  set: (values: string[]) => {
    const nextFilters: Record<string, string | number> = { ...urlState.filters.value }
    delete nextFilters.classification_text
    if (values.length) nextFilters.classification_text = values.join(',')
    urlState.filters.value = nextFilters
  },
})

function toggleSeverity(item: string) {
  const current = selectedSeverities.value
  selectedSeverities.value = current.includes(item) ? current.filter(i => i !== item) : [...current, item]
}

function toggleServer(item: string) {
  const current = selectedServers.value
  selectedServers.value = current.includes(item) ? current.filter(i => i !== item) : [...current, item]
}

function toggleClassification(item: string) {
  const current = selectedClassifications.value
  selectedClassifications.value = current.includes(item) ? current.filter(i => i !== item) : [...current, item]
}

// Classification virtual scrolling for 400+ items
const classificationSearch = ref('')

const filteredClassifications = computed(() => {
  const search = classificationSearch.value.trim().toLowerCase()
  const all = classificationsData.value
  const filtered = search ? all.filter(c => c.toLowerCase().includes(search)) : all
  return filtered.toSorted((a, b) => {
    const aSelected = selectedClassifications.value.includes(a)
    const bSelected = selectedClassifications.value.includes(b)
    return aSelected === bSelected ? 0 : aSelected ? -1 : 1
  })
})

const { list: virtualClassifications, containerProps, wrapperProps } = useVirtualList(filteredClassifications, { itemHeight: 32, overscan: 5 })

watch(classificationOpen, (open) => {
  if (!open) classificationSearch.value = ''
})

// IP filters need draft state for text input UX (commit on blur/enter)
// Initialize empty and sync from URL state via watchers to handle SSR hydration correctly
const sourceIpDraft = ref('')
const targetIpDraft = ref('')

watch(() => urlState.filters.value.source_ipv4, v => { sourceIpDraft.value = String(v ?? '') }, { immediate: true })
watch(() => urlState.filters.value.target_ipv4, v => { targetIpDraft.value = String(v ?? '') }, { immediate: true })

const sourceIpHint = computed(() => getIPFilterHint(sourceIpDraft.value))
const targetIpHint = computed(() => getIPFilterHint(targetIpDraft.value))

function applySourceIp() {
  const value = sourceIpDraft.value.trim()
  const nextFilters: Record<string, string | number> = { ...urlState.filters.value }
  delete nextFilters.source_ipv4
  if (value) nextFilters.source_ipv4 = value
  urlState.filters.value = nextFilters
}

function applyTargetIp() {
  const value = targetIpDraft.value.trim()
  const nextFilters: Record<string, string | number> = { ...urlState.filters.value }
  delete nextFilters.target_ipv4
  if (value) nextFilters.target_ipv4 = value
  urlState.filters.value = nextFilters
}

function clearSourceIp() {
  sourceIpDraft.value = ''
  applySourceIp()
}

function clearTargetIp() {
  targetIpDraft.value = ''
  applyTargetIp()
}

const requireIps = computed(() => {
  const val = urlState.filters.value.require_ips
  return val === undefined || val === 'true' || val === 1 || val === '1'
})

function setRequireIps(checked: boolean) {
  const nextFilters: Record<string, string | number> = { ...urlState.filters.value }
  if (checked) {
    delete nextFilters.require_ips
  } else {
    nextFilters.require_ips = 'false'
    if (urlState.view.value === 'grouped') {
      urlState.view.value = 'ungrouped'
    }
  }
  urlState.filters.value = nextFilters
}

// Active filter badges
const activeFilters = computed(() => {
  const result: { key: string; label: string; color?: string; icon?: string }[] = []

  for (const s of selectedSeverities.value) {
    result.push({ key: `severity:${s}`, label: formatSeverity(s), color: getSeverityDotColor(s) })
  }
  for (const srv of selectedServers.value) {
    result.push({ key: `server:${srv}`, label: srv, icon: 'lucide:server' })
  }
  for (const c of selectedClassifications.value) {
    result.push({ key: `classification:${c}`, label: c.length <= 20 ? c : `${c.slice(0, 20)}…`, icon: 'lucide:tag' })
  }
  if (urlState.filters.value.source_ipv4) {
    result.push({ key: 'source_ipv4', label: String(urlState.filters.value.source_ipv4), icon: 'lucide:arrow-up-right' })
  }
  if (urlState.filters.value.target_ipv4) {
    result.push({ key: 'target_ipv4', label: String(urlState.filters.value.target_ipv4), icon: 'lucide:arrow-down-right' })
  }
  if (!requireIps.value) {
    result.push({ key: 'require_ips', label: 'All alerts', icon: 'lucide:globe' })
  }
  return result
})

function clearFilter(key: string) {
  if (key === 'source_ipv4') return clearSourceIp()
  if (key === 'target_ipv4') return clearTargetIp()
  if (key === 'require_ips') return setRequireIps(true)

  const [type, value] = key.split(':')
  if (type === 'severity') selectedSeverities.value = selectedSeverities.value.filter(v => v !== value)
  if (type === 'server') selectedServers.value = selectedServers.value.filter(v => v !== value)
  if (type === 'classification') selectedClassifications.value = selectedClassifications.value.filter(v => v !== value)
}

function clearAllFilters() {
  sourceIpDraft.value = ''
  targetIpDraft.value = ''
  const nextFilters: Record<string, string | number> = { ...urlState.filters.value }
  delete nextFilters.severity
  delete nextFilters.server
  delete nextFilters.classification_text
  delete nextFilters.source_ipv4
  delete nextFilters.target_ipv4
  delete nextFilters.require_ips
  urlState.filters.value = nextFilters
}
</script>

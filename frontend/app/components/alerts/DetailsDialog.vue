<script setup lang="ts">
import { formatTimestamp } from '@/utils/timestampFormatter'
import { shortAlertId, snortRuleDocUrl } from '@/utils/alertDetail'

const props = defineProps<{
  alertId?: string | null
  open: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

// Injected context must be resolved during setup, not inside event handlers
const { urlState } = useAlertTableContext()
const route = useRoute()

// Reactive state
const loading = ref(false)
const error = ref<string | null>(null)
const alertData = ref<AlertDetail | null>(null)
const activeTab = ref('overview')

// Abort controller for cancelling stale requests
let abortController: AbortController | null = null

// Model for dialog open state
const dialogOpen = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value)
})

function flowSide(bytes?: number | null, packets?: number | null): string | null {
  return bytes == null && packets == null ? null : `${bytes ?? '?'} bytes in ${packets ?? '?'} packets`
}

const hasIpPair = computed(() => Boolean(
  alertData.value?.source?.address && alertData.value.target?.address,
))

const ruleDocUrl = computed(() => snortRuleDocUrl(alertData.value?.rule.id))
const rawEvent = computed(() => JSON.stringify(alertData.value?.document ?? {}, null, 2))
const endpoints = computed(() => [
  { key: 'src', label: 'Source', data: alertData.value?.source },
  { key: 'tgt', label: 'Target', data: alertData.value?.target },
])
const networkRows = computed(() => {
  const n = alertData.value?.network
  const rows: [string, string | number | null | undefined][] = [
    ['Transport', n?.transport],
    ['Protocol', n?.protocol],
    ['VLAN', n?.vlan_id],
    ['Bytes', n?.bytes],
    ['Packets', n?.packets],
  ]
  return rows.filter(([, value]) => value != null)
})
const flowRows = computed(() => {
  const f = alertData.value?.flow
  const rows: [string, string | null | undefined][] = [
    ['Direction', f?.direction],
    ['Started', f?.started_at ? formatTimestamp(f.started_at) : null],
    ['Client', flowSide(f?.client_bytes, f?.client_packets)],
    ['Server', flowSide(f?.server_bytes, f?.server_packets)],
  ]
  return rows.filter(([, value]) => value != null)
})
const additionalRow = 'grid grid-cols-[180px_minmax(0,_1fr)] gap-x-4 gap-y-2 text-sm items-start'
const packetRows = computed(() => Object.entries(alertData.value?.packet ?? {}))

// Fetch alert details when dialog opens or alert changes
watch(
  [() => props.alertId, () => dialogOpen.value],
  async ([id, isOpen]) => {
    // Abort any in-flight request before starting a new one
    abortController?.abort()

    if (!id || !isOpen) {
      return
    }
    await fetchAlertDetails(id)
  },
  { immediate: true },
)

// Cleanup on unmount
onUnmounted(() => {
  abortController?.abort()
})

async function fetchAlertDetails(id: string) {
  // Create new abort controller for this request
  abortController = new AbortController()
  const signal = abortController.signal

  loading.value = true
  error.value = null

  try {
    const data = await $fetch<AlertDetail>(`/api/alerts/${id}`, { signal })
    // Only update if request wasn't aborted
    if (!signal.aborted) {
      alertData.value = data
    }
  } catch (err) {
    // Ignore abort errors - they're expected when user switches alerts quickly
    if (err instanceof Error && err.name === 'AbortError') {
      return
    }
    console.error('Failed to fetch alert details:', err)
    error.value = 'Failed to load alert details. Please try again.'
  } finally {
    // Only clear loading if this request wasn't aborted
    if (!signal.aborted) {
      loading.value = false
    }
  }
}

// Helper functions
const copied = ref<Record<string, boolean>>({})

async function copyWithFeedback(key: string, text: string) {
  await navigator.clipboard.writeText(text)
  copied.value[key] = true
  setTimeout(() => (copied.value[key] = false), 1500)
}

// Timestamp formatting handled by centralized utility

function getSeverityPillClass(severity?: string | null): string {
  const s = (severity || 'low').toLowerCase()
  const map: Record<string, string> = {
    high: 'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-primary text-primary-foreground',
    medium: 'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-accent text-accent-foreground',
    low: 'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-muted text-muted-foreground',
  }
  return map[s] || map.low!
}

async function viewAllFromPair() {
  if (!alertData.value?.source?.address || !alertData.value.target?.address) return

  await urlState.navigateTo({
    query: {
      ...route.query,
      view: 'ungrouped',
      page: '1',
      size: '100',
      sort: 'detected_at:desc',
      filter: JSON.stringify({
        source_ipv4: alertData.value.source.address,
        target_ipv4: alertData.value.target.address,
      }),
    },
  })

  // Close the dialog after navigation
  dialogOpen.value = false
}

</script>

<template>
  <Dialog v-model:open="dialogOpen">
    <DialogContent class="sm:max-w-4xl lg:max-w-5xl xl:max-w-6xl max-h-[85vh] overflow-hidden flex flex-col">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          <Icon name="lucide:shield" class="h-5 w-5 text-primary" />
          Alert Details
          <span v-if="alertData" class="text-sm text-muted-foreground ml-2" :title="alertData.id">
            #{{ shortAlertId(alertData.id) }}
          </span>
        </DialogTitle>
        <DialogDescription v-if="alertData">
          {{ alertData.classification_text || 'Security Alert' }}
        </DialogDescription>
      </DialogHeader>

      <div class="flex-1 overflow-y-auto">
        <!-- Compact summary bar -->
        <div v-if="alertData" class="rounded-md border px-4 py-3 mb-4">
          <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div class="flex items-center gap-2 min-w-0">
              <span class="text-xs text-muted-foreground">Severity</span>
              <span :class="getSeverityPillClass(alertData.severity)">{{ alertData.severity?.toUpperCase() || 'UNKNOWN' }}</span>
            </div>
            <div class="flex items-center gap-2 min-w-0">
              <Icon name="lucide:clock" class="h-4 w-4 text-muted-foreground" />
              <span class="truncate text-sm" :title="formatTimestamp(alertData.detected_at.timestamp)">
                {{ formatTimestamp(alertData.detected_at.timestamp) }}
              </span>
            </div>
            <div class="flex items-center gap-2 min-w-0">
              <Icon name="lucide:globe" class="h-4 w-4 text-muted-foreground" />
              <span class="text-xs text-muted-foreground">Path</span>
              <span class="font-mono text-sm truncate" :title="`${alertData.source?.address || 'Unknown'} -> ${alertData.target?.address || 'Unknown'}`">
                {{ alertData.source?.address || 'Unknown' }}
              </span>
              <Icon name="lucide:arrow-right" class="h-4 w-4 text-muted-foreground shrink-0" />
              <span class="font-mono text-sm truncate" :title="alertData.target?.address || 'Unknown'">
                {{ alertData.target?.address || 'Unknown' }}
              </span>
            </div>

            <div
              v-if="alertData.forwarded?.true_source"
              class="flex items-center gap-2 min-w-0"
            >
              <Icon name="lucide:fingerprint" class="h-4 w-4 text-primary shrink-0" />
              <span class="text-xs text-muted-foreground">True source</span>
              <span
                class="font-mono text-sm truncate text-primary"
                :title="`Real client from X-Forwarded-For (via ${alertData.forwarded.via_proxy || 'proxy'}). Header-supplied — verify before acting.`"
              >
                {{ alertData.forwarded.true_source }}
              </span>
            </div>

            <div class="flex items-center gap-2 min-w-0 sm:col-span-2 lg:col-span-3">
              <span class="text-xs text-muted-foreground">Classification</span>
              <span class="text-sm font-medium truncate" :title="alertData.classification_text || 'N/A'">
                {{ alertData.classification_text || 'N/A' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Loading state -->
        <div v-if="loading" class="flex items-center justify-center py-8">
          <div class="text-center space-y-4">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
            <p class="text-sm text-muted-foreground">Loading alert details...</p>
          </div>
        </div>

        <!-- Error state -->
        <div v-else-if="error" class="flex items-center justify-center py-8">
          <div class="text-center space-y-4">
            <Icon name="lucide:alert-triangle" class="h-12 w-12 text-destructive mx-auto" />
            <p class="text-sm text-destructive">{{ error }}</p>
          </div>
        </div>

        <!-- Alert content -->
        <div v-else-if="alertData" class="space-y-6">
          <Tabs v-model:model-value="activeTab" class="w-full">
            <TabsList class="grid w-full grid-cols-3 sticky top-0 z-10 border-b">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="network">Network</TabsTrigger>
              <TabsTrigger value="additional">Additional</TabsTrigger>
            </TabsList>

            <!-- Overview Tab -->
            <TabsContent value="overview" class="space-y-4 mt-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <!-- Basic Information -->
                <Card>
                  <CardHeader class="pb-3">
                    <CardTitle class="text-sm font-medium">Basic Information</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-sm">
                      <span class="text-muted-foreground">Severity</span>
                      <span>
                        <span :class="getSeverityPillClass(alertData.severity)">{{ alertData.severity?.toUpperCase() || 'UNKNOWN' }}</span>
                      </span>

                      <span class="text-muted-foreground">Classification</span>
                      <span class="font-medium">{{ alertData.classification_text || 'N/A' }}</span>

                      <template v-if="alertData.rule.id">
                        <span class="text-muted-foreground">Rule</span>
                        <span class="flex items-center gap-2 min-w-0">
                          <span class="font-mono break-all">
                            {{ alertData.rule.id }}<template v-if="alertData.rule.version"> (rev {{ alertData.rule.version }})</template>
                          </span>
                          <a
                            v-if="ruleDocUrl"
                            :href="ruleDocUrl"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="inline-flex items-center gap-1 text-primary hover:underline"
                          >
                            Docs
                            <Icon name="lucide:external-link" class="h-3 w-3" />
                          </a>
                        </span>
                      </template>

                      <template v-if="alertData.rule.category">
                        <span class="text-muted-foreground">Category</span>
                        <span>{{ alertData.rule.category }}</span>
                      </template>

                      <template v-if="alertData.action">
                        <span class="text-muted-foreground">Action</span>
                        <span>{{ alertData.action }}</span>
                      </template>

                      <template v-if="alertData.http_request">
                        <span class="text-muted-foreground">Request</span>
                        <span class="flex items-center gap-1 min-w-0">
                          <span class="font-mono break-all">{{ alertData.http_request }}</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            class="h-6 w-6 p-0 shrink-0"
                            aria-label="Copy request line"
                            @click="copyWithFeedback('request', alertData.http_request)"
                          >
                            <Icon v-if="copied['request']" name="lucide:check" class="h-3 w-3 text-primary" />
                            <Icon v-else name="lucide:copy" class="h-3 w-3" />
                          </Button>
                        </span>
                      </template>

                      <span class="text-muted-foreground">Alert ID</span>
                      <span class="flex items-center gap-1 min-w-0">
                        <span class="font-mono" :title="alertData.id">{{ shortAlertId(alertData.id) }}</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          class="h-6 w-6 p-0 shrink-0"
                          aria-label="Copy alert id"
                          @click="copyWithFeedback('alert-id', alertData.id)"
                        >
                          <Icon v-if="copied['alert-id']" name="lucide:check" class="h-3 w-3 text-primary" />
                          <Icon v-else name="lucide:copy" class="h-3 w-3" />
                        </Button>
                      </span>
                    </div>
                  </CardContent>
                </Card>

                <!-- Detection -->
                <Card>
                  <CardHeader class="pb-3">
                    <CardTitle class="text-sm font-medium flex items-center gap-2">
                      <Icon name="lucide:clock" class="h-4 w-4" />
                      Detection
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-sm">
                      <span class="text-muted-foreground">Detected</span>
                      <span class="font-medium">{{ formatTimestamp(alertData.detected_at.timestamp) }}</span>

                      <template v-if="alertData.analyzer.name">
                        <span class="text-muted-foreground">Sensor</span>
                        <span>{{ alertData.analyzer.name }}</span>
                      </template>

                      <template v-if="alertData.analyzer.interface">
                        <span class="text-muted-foreground">Interface</span>
                        <span>{{ alertData.analyzer.interface }}</span>
                      </template>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <!-- Network Tab -->
            <TabsContent value="network" class="space-y-4 mt-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card v-for="endpoint in endpoints" :key="endpoint.key">
                  <CardHeader class="pb-3">
                    <CardTitle class="text-sm font-medium flex items-center gap-2">
                      <Icon name="lucide:globe" class="h-4 w-4" />
                      {{ endpoint.label }}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div v-if="endpoint.data" class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-sm">
                      <span class="text-muted-foreground">IP Address</span>
                      <span class="flex items-center gap-1">
                        <span class="font-mono break-all">{{ endpoint.data.address }}</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          class="h-6 w-6 p-0 shrink-0"
                          :aria-label="`Copy ${endpoint.label.toLowerCase()} IP`"
                          @click="copyWithFeedback(`${endpoint.key}-ip`, endpoint.data.address)"
                        >
                          <Icon v-if="copied[`${endpoint.key}-ip`]" name="lucide:check" class="h-3 w-3 text-primary" />
                          <Icon v-else name="lucide:copy" class="h-3 w-3" />
                        </Button>
                      </span>

                      <template v-if="endpoint.key === 'src' && alertData.forwarded?.true_source">
                        <span class="text-muted-foreground flex items-center gap-1">
                          <Icon name="lucide:fingerprint" class="h-3.5 w-3.5 text-primary" />
                          True Source
                        </span>
                        <span class="flex items-center gap-1 min-w-0">
                          <span class="font-mono break-all text-primary">{{ alertData.forwarded.true_source }}</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            class="h-6 w-6 p-0 shrink-0"
                            aria-label="Copy true source IP"
                            @click="copyWithFeedback('true-src', alertData.forwarded.true_source)"
                          >
                            <Icon v-if="copied['true-src']" name="lucide:check" class="h-3 w-3 text-primary" />
                            <Icon v-else name="lucide:copy" class="h-3 w-3" />
                          </Button>
                          <span
                            class="ml-0.5 inline-flex items-center rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary"
                            title="Recovered from the X-Forwarded-For header. Header-supplied, so treat as advisory — verify before acting."
                          >via proxy</span>
                        </span>
                      </template>

                      <template v-if="endpoint.key === 'src' && (alertData.forwarded?.forwarded_for?.length || 0) > 1">
                        <span class="text-muted-foreground">Forwarded chain</span>
                        <span class="font-mono text-xs break-all">{{ alertData.forwarded?.forwarded_for.join(' → ') }}</span>
                      </template>

                      <template v-if="endpoint.key === 'src' && alertData.forwarded?.via_proxy">
                        <span class="text-muted-foreground">Via proxy</span>
                        <span class="text-xs break-all">{{ alertData.forwarded.via_proxy }}</span>
                      </template>

                      <template v-if="endpoint.data.port != null">
                        <span class="text-muted-foreground">Port</span>
                        <span>{{ endpoint.data.port }}</span>
                      </template>

                      <template v-if="endpoint.data.mac">
                        <span class="text-muted-foreground">MAC</span>
                        <span class="font-mono break-all">{{ endpoint.data.mac }}</span>
                      </template>
                    </div>
                    <div v-else class="text-sm text-muted-foreground">No {{ endpoint.label.toLowerCase() }} information</div>
                  </CardContent>
                </Card>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card v-if="networkRows.length > 0">
                  <CardHeader class="pb-3">
                    <CardTitle class="text-sm font-medium">Traffic</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-sm">
                      <template v-for="[label, value] in networkRows" :key="label">
                        <span class="text-muted-foreground">{{ label }}</span>
                        <span>{{ value }}</span>
                      </template>
                    </div>
                  </CardContent>
                </Card>

                <Card v-if="flowRows.length > 0">
                  <CardHeader class="pb-3">
                    <CardTitle class="text-sm font-medium">Flow</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-sm">
                      <template v-for="[label, value] in flowRows" :key="label">
                        <span class="text-muted-foreground">{{ label }}</span>
                        <span>{{ value }}</span>
                      </template>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <!-- Additional Data Tab -->
            <TabsContent value="additional" class="mt-4">
              <Card>
                <CardHeader class="pb-3">
                  <CardTitle class="text-sm font-medium">Additional Data</CardTitle>
                </CardHeader>
                <CardContent>
                  <div class="space-y-2">
                    <div v-if="alertData.http_request" :class="additionalRow">
                      <span class="font-mono text-muted-foreground">http_request</span>
                      <span class="flex items-start gap-1 min-w-0">
                        <span class="font-mono break-all">{{ alertData.http_request }}</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          class="h-6 w-6 p-0 shrink-0"
                          aria-label="Copy http_request"
                          @click="copyWithFeedback('http-request', alertData.http_request)"
                        >
                          <Icon v-if="copied['http-request']" name="lucide:check" class="h-3 w-3 text-primary" />
                          <Icon v-else name="lucide:copy" class="h-3 w-3" />
                        </Button>
                      </span>
                    </div>

                    <div v-if="alertData.payload" :class="additionalRow">
                      <span class="font-mono text-muted-foreground">payload</span>
                      <AlertsHexAsciiPayload
                        :payload="alertData.payload"
                        :name="`alert-${shortAlertId(alertData.id)}.bin`"
                        class="min-w-0 max-w-full"
                      />
                    </div>

                    <div v-for="[name, value] in packetRows" :key="name" :class="additionalRow">
                      <span class="font-mono text-muted-foreground break-words">{{ name }}</span>
                      <span class="break-words">{{ value }}</span>
                    </div>

                    <div :class="additionalRow">
                      <span class="font-mono text-muted-foreground">event</span>
                      <div class="relative min-w-0">
                        <pre class="rounded border p-3 text-xs overflow-auto max-h-64 max-w-full whitespace-pre pr-10"><code>{{ rawEvent }}</code></pre>
                        <div class="absolute top-2 right-2">
                          <Button
                            variant="outline"
                            size="sm"
                            class="h-7 px-2"
                            aria-label="Copy event"
                            @click="copyWithFeedback('raw', rawEvent)"
                          >
                            <Icon v-if="copied['raw']" name="lucide:check" class="h-3.5 w-3.5 text-primary" />
                            <Icon v-else name="lucide:copy" class="h-3.5 w-3.5" />
                            <span class="sr-only">Copy event</span>
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      <DialogFooter
        :class="[
          'mt-4 border-t pt-4 gap-2 flex-col sm:flex-row sm:items-center',
          hasIpPair ? 'sm:justify-between' : 'sm:justify-end',
        ]"
      >
        <Button
          v-if="hasIpPair"
          variant="outline"
          class="w-full sm:w-auto"
          @click="viewAllFromPair"
        >
          <Icon name="lucide:list" class="mr-2 size-4" />
          View all from IP pair
        </Button>
        <DialogClose as-child>
          <Button variant="outline" class="w-full sm:w-auto">
            Close
          </Button>
        </DialogClose>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

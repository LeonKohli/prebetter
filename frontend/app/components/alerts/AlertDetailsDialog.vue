<script setup lang="ts">
import HexAsciiPayload from '@/components/alerts/HexAsciiPayload.vue'
import { formatTimestamp } from '@/utils/timestampFormatter'

const props = defineProps<{
  alertId?: string | null
  open: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

// Reactive state
const loading = ref(false)
const error = ref<string | null>(null)
const alertData = ref<AlertDetail | null>(null)
const activeTab = ref('overview')

// Model for dialog open state
const dialogOpen = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value)
})

const hasIpPair = computed(() => Boolean(
  alertData.value?.source?.address && alertData.value?.target?.address,
))

// Fetch alert details when dialog opens or alert changes
watch(
  [() => props.alertId, () => dialogOpen.value],
  async ([id, isOpen]) => {
    if (!id || !isOpen) {
      return
    }
    await fetchAlertDetails(id)
  },
  { immediate: true },
)

async function fetchAlertDetails(id: string) {
  loading.value = true
  error.value = null
  
  try {
    // $fetch returns the data directly, not wrapped
    const data = await $fetch<AlertDetail>(`/api/alerts/${id}`)
    alertData.value = data
  } catch (err) {
    console.error('Failed to fetch alert details:', err)
    error.value = 'Failed to load alert details. Please try again.'
  } finally {
    loading.value = false
  }
}

// Helper functions
const copied = reactive<Record<string, boolean>>({})

function copyWithFeedback(key: string, text: string) {
  navigator.clipboard.writeText(text)
  copied[key] = true
  window.setTimeout(() => {
    copied[key] = false
  }, 1500)
}

// Timestamp formatting handled by centralized utility

function getSeverityClass(severity?: string): string {
  const severityLower = severity?.toLowerCase()
  switch (severityLower) {
    case 'high':
      return 'text-destructive font-semibold'
    case 'medium':
      return 'text-accent font-semibold'
    case 'low':
      return 'text-muted-foreground font-semibold'
    default:
      return 'text-muted-foreground'
  }
}

// Match table severity styling for a consistent pill look
function getSeverityPillClass(severity?: string): string {
  const s = (severity || 'low').toLowerCase()
  const map: Record<string, string> = {
    high: 'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-primary text-primary-foreground',
    medium: 'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-accent text-accent-foreground',
    low: 'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-muted text-muted-foreground',
  }
  return map[s] || map.low!
}

async function viewAllFromPair() {
  if (!alertData.value?.source?.address || !alertData.value?.target?.address) return

  const router = useRouter()
  const route = useRoute()

  await router.push({
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

function isHttpLikePayload(key: string, value: unknown): boolean {
  if (typeof value !== 'string') return false
  const k = key.toLowerCase()
  if (k.includes('payload') || k.includes('headers')) return true
  return /HTTP\/\d\.\d|\b(GET|POST|PUT|DELETE|HEAD|PATCH)\s+\S+\s+HTTP\/\d\.\d|\bUser-Agent:|\bHost:|\bAccept:/i.test(value)
}

function formatHttpLikePayload(raw: string): string {
  let str = String(raw).trim()
  // Ensure a line break after the request line if present
  str = str.replace(/(HTTP\/\d\.\d)(\s+)/, '$1\n')
  // Insert a newline before HTTP method tokens if glued to a prefix (e.g., "payloadGET")
  str = str.replace(/(\w)(\b(GET|POST|PUT|DELETE|HEAD|PATCH)\s+)/g, '$1\n$2')
  // Start new lines before headers like "Key: value"
  str = str.replace(/\s([A-Za-z0-9_-]+):\s/g, '\n$1: ')
  // Normalize multiple spaces
  str = str.replace(/\n\s+/g, '\n')
  return str
}
</script>

<template>
  <Dialog v-model:open="dialogOpen">
    <DialogContent class="sm:max-w-4xl lg:max-w-5xl xl:max-w-6xl max-h-[85vh] overflow-hidden flex flex-col">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          <Icon name="lucide:shield" class="h-5 w-5 text-primary" />
          Alert Details
          <span v-if="alertData" class="text-sm text-muted-foreground ml-2">
            #{{ alertData.id }}
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
            
            <div class="flex items-center gap-2 min-w-0 sm:col-span-2 lg:col-span-3">
              <span class="text-xs text-muted-foreground">Classification</span>
              <span class="text-sm font-medium truncate" :title="alertData.classification_text || 'N/A'">
                {{ alertData.classification_text || 'N/A' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Correlation Description (if present) -->
        <div v-if="alertData?.correlation_description" class="rounded-md bg-accent/50 border border-accent px-4 py-3 mb-4">
          <div class="flex items-start gap-2">
            <Icon name="lucide:activity" class="h-5 w-5 text-accent-foreground shrink-0 mt-0.5" />
            <div class="flex-1 min-w-0">
              <h4 class="text-sm font-semibold text-accent-foreground mb-1">Correlation Analysis</h4>
              <p class="text-sm text-accent-foreground/80">{{ alertData.correlation_description }}</p>
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
          <!-- Tabs for different sections -->
          <Tabs v-model:model-value="activeTab" class="w-full">
            <TabsList class="grid w-full grid-cols-2 sm:grid-cols-3 md:grid-cols-5 sticky top-0 z-10 border-b">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="network">Network</TabsTrigger>
              <TabsTrigger value="analyzers">Analyzers</TabsTrigger>
              <TabsTrigger value="references">References</TabsTrigger>
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

                      <span class="text-muted-foreground">Message ID</span>
                      <span class="flex items-center gap-1 min-w-0">
                      <span class="font-mono break-all">{{ alertData.message_id }}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        class="h-6 w-6 p-0 shrink-0"
                        aria-label="Copy message id"
                        @click="copyWithFeedback('msg-basic', alertData.message_id)"
                      >
                        <Icon v-if="copied['msg-basic']" name="lucide:check" class="h-3 w-3 text-primary" />
                        <Icon v-else name="lucide:copy" class="h-3 w-3" />
                      </Button>
                      </span>
                    </div>
                  </CardContent>
                </Card>

                <!-- Timestamps -->
                <Card>
                  <CardHeader class="pb-3">
                    <CardTitle class="text-sm font-medium flex items-center gap-2">
                      <Icon name="lucide:clock" class="h-4 w-4" />
                      Timestamps
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-sm">
                      <span class="text-muted-foreground">Detected</span>
                      <span class="font-medium">{{ formatTimestamp(alertData.detected_at.timestamp) }}</span>

                      <template v-if="alertData.created_at">
                        <span class="text-muted-foreground">Created</span>
                        <span class="font-medium">{{ formatTimestamp(alertData.created_at.timestamp) }}</span>
                      </template>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <!-- Impact Information -->
              <Card v-if="alertData.description || alertData.impact_type">
                <CardHeader class="pb-3">
                  <CardTitle class="text-sm font-medium">Impact Details</CardTitle>
                </CardHeader>
                <CardContent class="space-y-2">
                  <div v-if="alertData.impact_type">
                    <span class="text-sm text-muted-foreground">Type:</span>
                    <span class="text-sm font-medium ml-2">{{ alertData.impact_type }}</span>
                  </div>
                  <div v-if="alertData.description">
                    <span class="text-sm text-muted-foreground">Description:</span>
                    <p class="text-sm mt-1">{{ alertData.description }}</p>
                  </div>
                  <div v-if="alertData.completion">
                    <span class="text-sm text-muted-foreground">Completion:</span>
                    <span class="text-sm font-medium ml-2">{{ alertData.completion }}</span>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <!-- Network Tab -->
            <TabsContent value="network" class="space-y-4 mt-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <!-- Source Information -->
                <Card>
                  <CardHeader class="pb-3">
                    <CardTitle class="text-sm font-medium flex items-center gap-2">
                      <Icon name="lucide:globe" class="h-4 w-4" />
                      Source
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div v-if="alertData.source">
                      <div class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-sm">
                        <span class="text-muted-foreground">IP Address</span>
                        <span class="flex items-center gap-1">
                          <span class="font-mono break-all">{{ alertData.source.address || 'Unknown' }}</span>
                          <Button
                            v-if="alertData.source.address"
                            variant="ghost"
                            size="sm"
                            class="h-6 w-6 p-0 shrink-0"
                            aria-label="Copy source IP"
                            @click="copyWithFeedback('src-ip', alertData.source.address)"
                          >
                            <Icon v-if="copied['src-ip']" name="lucide:check" class="h-3 w-3 text-primary" />
                            <Icon v-else name="lucide:copy" class="h-3 w-3" />
                          </Button>
                        </span>

                        <template v-if="alertData.source.interface">
                          <span class="text-muted-foreground">Interface</span>
                          <span>{{ alertData.source.interface }}</span>
                        </template>

                        <template v-if="alertData.source.protocol">
                          <span class="text-muted-foreground">Protocol</span>
                          <span>{{ alertData.source.protocol }}</span>
                        </template>

                        <template v-if="alertData.source.node?.name">
                          <span class="text-muted-foreground">Node</span>
                          <span>{{ alertData.source.node.name }}</span>
                        </template>
                      </div>
                    </div>
                    <div v-else class="text-sm text-muted-foreground">No source information</div>
                  </CardContent>
                </Card>

                <!-- Target Information -->
                <Card>
                  <CardHeader class="pb-3">
                    <CardTitle class="text-sm font-medium flex items-center gap-2">
                      <Icon name="lucide:globe" class="h-4 w-4" />
                      Target
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div v-if="alertData.target">
                      <div class="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-sm">
                        <span class="text-muted-foreground">IP Address</span>
                        <span class="flex items-center gap-1">
                          <span class="font-mono break-all">{{ alertData.target.address || 'Unknown' }}</span>
                          <Button
                            v-if="alertData.target.address"
                            variant="ghost"
                            size="sm"
                            class="h-6 w-6 p-0 shrink-0"
                            aria-label="Copy target IP"
                            @click="copyWithFeedback('tgt-ip', alertData.target.address)"
                          >
                            <Icon v-if="copied['tgt-ip']" name="lucide:check" class="h-3 w-3 text-primary" />
                            <Icon v-else name="lucide:copy" class="h-3 w-3" />
                          </Button>
                        </span>

                        <template v-if="alertData.target.interface">
                          <span class="text-muted-foreground">Interface</span>
                          <span>{{ alertData.target.interface }}</span>
                        </template>

                        <template v-if="alertData.target.protocol">
                          <span class="text-muted-foreground">Protocol</span>
                          <span>{{ alertData.target.protocol }}</span>
                        </template>

                        <template v-if="alertData.target.node?.name">
                          <span class="text-muted-foreground">Node</span>
                          <span>{{ alertData.target.node.name }}</span>
                        </template>
                      </div>
                    </div>
                    <div v-else class="text-sm text-muted-foreground">No target information</div>
                  </CardContent>
                </Card>
              </div>

              <!-- Services -->
              <Card v-if="alertData.services.length > 0">
                <CardHeader class="pb-3">
                  <CardTitle class="text-sm font-medium">Services</CardTitle>
                </CardHeader>
                <CardContent>
                  <div class="space-y-2">
                    <div v-for="(service, idx) in alertData.services" :key="idx" class="flex items-center gap-3 text-sm flex-wrap">
                      <Badge variant="outline">{{ service.direction }}</Badge>
                      <span class="font-medium">Port {{ service.port }}</span>
                      <span v-if="service.protocol" class="text-muted-foreground">{{ service.protocol }}</span>
                      <span v-if="service.name" class="">{{ service.name }}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <!-- Analyzers Tab -->
            <TabsContent value="analyzers" class="mt-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card v-for="(analyzer, idx) in alertData.analyzers" :key="idx">
                <CardHeader class="pb-3">
                  <CardTitle class="text-sm font-medium flex items-center gap-2">
                    <Icon name="lucide:server" class="h-4 w-4" />
                    {{ analyzer.name }}
                  </CardTitle>
                </CardHeader>
                <CardContent class="space-y-2">
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                    <div v-if="analyzer.model">
                      <span class="text-muted-foreground">Model:</span>
                      <span class="ml-2">{{ analyzer.model }}</span>
                    </div>
                    <div v-if="analyzer.version">
                      <span class="text-muted-foreground">Version:</span>
                      <span class="ml-2">{{ analyzer.version }}</span>
                    </div>
                    <div v-if="analyzer.class_type">
                      <span class="text-muted-foreground">Class:</span>
                      <span class="ml-2">{{ analyzer.class_type }}</span>
                    </div>
                    <div v-if="analyzer.analyzer_id">
                      <span class="text-muted-foreground">ID:</span>
                      <span class="ml-2 font-mono">{{ analyzer.analyzer_id }}</span>
                    </div>
                  </div>
                  <div v-if="analyzer.node" class="pt-2 border-t">
                    <p class="text-sm font-medium mb-1">Node Information</p>
                    <div class="text-sm space-y-1">
                      <div v-if="analyzer.node.name">
                        <span class="text-muted-foreground">Name:</span>
                        <span class="ml-2">{{ analyzer.node.name }}</span>
                      </div>
                      <div v-if="analyzer.node.location">
                        <span class="text-muted-foreground">Location:</span>
                        <span class="ml-2">{{ analyzer.node.location }}</span>
                      </div>
                      <div v-if="analyzer.node.os">
                        <span class="text-muted-foreground">OS:</span>
                        <span class="ml-2">{{ analyzer.node.os }}</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
              </div>
            </TabsContent>

            <!-- References Tab -->
            <TabsContent value="references" class="space-y-4 mt-4">
              <Card v-if="alertData.references.length > 0">
                <CardHeader class="pb-3">
                  <CardTitle class="text-sm font-medium flex items-center gap-2">
                    <Icon name="lucide:file-text" class="h-4 w-4" />
                    References
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div class="space-y-2">
                    <div v-for="(ref, idx) in alertData.references" :key="idx" class="flex items-start gap-2">
                      <Icon name="lucide:external-link" class="h-4 w-4 mt-0.5 text-muted-foreground" />
                      <div class="flex-1">
                        <a 
                          v-if="ref.url"
                          :href="ref.url"
                          target="_blank"
                          rel="noopener noreferrer"
                          class="text-sm text-primary hover:underline"
                        >
                          {{ ref.name || ref.url }}
                        </a>
                         <span v-else class="text-sm">{{ ref.name || 'Unknown reference' }}</span>
                         <Badge v-if="ref.origin" variant="outline" class="ml-2">{{ ref.origin }}</Badge>
                       </div>
                     </div>
                   </div>
                 </CardContent>
               </Card>
              <div v-else class="text-center py-8 text-sm text-muted-foreground">
                No references available for this alert
              </div>

              <!-- Web Services -->
              <Card v-if="alertData.web_services.length > 0">
                <CardHeader class="pb-3">
                  <CardTitle class="text-sm font-medium flex items-center gap-2">
                    <Icon name="lucide:globe" class="h-4 w-4" />
                    Web Services
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div class="space-y-2">
                    <div v-for="(ws, idx) in alertData.web_services" :key="idx" class="text-sm">
                      <div v-if="ws.url" class="flex items-start gap-2">
                        <span class="text-muted-foreground">URL:</span>
                        <a
                          :href="ws.url"
                          target="_blank"
                          rel="noopener noreferrer"
                          class="ml-2 font-mono text-primary break-all hover:underline"
                        >{{ ws.url }}</a>
                      </div>
                      <div v-if="ws.http_method">
                        <span class="text-muted-foreground">Method:</span>
                        <Badge variant="outline" class="ml-2">{{ ws.http_method }}</Badge>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <!-- Additional Data Tab -->
            <TabsContent value="additional" class="space-y-4 mt-4">
              <Card>
                <CardHeader class="pb-3">
                  <CardTitle class="text-sm font-medium">Additional Data</CardTitle>
                </CardHeader>
                <CardContent>
                  <div v-if="Object.keys(alertData.additional_data).length > 0" class="space-y-2">
                    <div
                      v-for="(value, key) in alertData.additional_data"
                      :key="key"
                      class="grid grid-cols-[180px_minmax(0,_1fr)] gap-x-4 gap-y-2 text-sm items-start"
                    >
                      <span class="font-mono text-muted-foreground break-words">{{ key }}</span>

                      <div class="min-w-0">
                        <!-- Dual-format payload (readable + original base64) -->
                        <HexAsciiPayload
                          v-if="value && typeof value === 'object' && ('readable' in (value as any) || 'original' in (value as any))"
                          :readable="(value as any).readable"
                          :original="(value as any).original"
                          :name="`${String(key)}.bin`"
                          class="max-w-full"
                        />

                        <!-- HTTP-like payloads nicely formatted -->
                        <div v-else-if="typeof value === 'string' && isHttpLikePayload(key, value)" class="relative min-w-0">
                          <pre class="rounded border p-3 text-xs overflow-auto max-h-64 max-w-full leading-relaxed whitespace-pre-wrap pr-10"><code>{{ formatHttpLikePayload(value) }}</code></pre>
                          <div class="absolute top-2 right-2">
                            <Button
                              variant="outline"
                              size="sm"
                              class="h-7 px-2"
                              aria-label="Copy payload"
                              @click="copyWithFeedback(`payload-${String(key)}`, formatHttpLikePayload(value))"
                            >
                              <Icon v-if="copied[`payload-${String(key)}`]" name="lucide:check" class="h-3.5 w-3.5 text-primary" />
                              <Icon v-else name="lucide:copy" class="h-3.5 w-3.5" />
                              <span class="sr-only">Copy payload</span>
                            </Button>
                          </div>
                        </div>

                        <!-- Plain strings -->
                        <span v-else-if="typeof value === 'string'" class="break-words whitespace-pre-wrap block">{{ value }}</span>

                        <!-- Objects pretty-printed -->
                        <pre v-else-if="typeof value === 'object'" class="rounded border p-3 text-xs overflow-auto max-h-64 max-w-full whitespace-pre"><code>{{ JSON.stringify(value, null, 2) }}</code></pre>

                        <!-- Fallback for other primitive types -->
                        <span v-else class="break-words block">{{ String(value) }}</span>
                      </div>
                    </div>
                  </div>
                  <div v-else class="text-sm text-muted-foreground">
                    No additional data available
                  </div>
                </CardContent>
              </Card>

              <!-- Alert Identifiers -->
              <Card v-if="alertData.alert_idents.length > 0">
                <CardHeader class="pb-3">
                  <CardTitle class="text-sm font-medium">Alert Identifiers</CardTitle>
                </CardHeader>
                <CardContent>
                  <div class="space-y-2">
                    <div v-for="(ident, idx) in alertData.alert_idents" :key="idx" class="text-sm">
                      <span class="text-muted-foreground">Alert ID:</span>
                      <span class="ml-2 font-mono">{{ ident.alertident }}</span>
                      <span v-if="ident.analyzerid" class="ml-4 text-muted-foreground">
                        Analyzer: {{ ident.analyzerid }}
                      </span>
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

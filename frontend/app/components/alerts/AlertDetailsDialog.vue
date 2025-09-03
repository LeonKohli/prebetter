<script setup lang="ts">
import type { AlertDetail } from '@/types/alerts'
import { Copy, ExternalLink, Shield, Network, Server, Clock, AlertTriangle, FileText, Globe } from 'lucide-vue-next'

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

// Fetch alert details when dialog opens
watch(() => props.alertId, async (newId) => {
  if (newId && props.open) {
    await fetchAlertDetails(newId)
  }
})

watch(dialogOpen, async (isOpen) => {
  if (isOpen && props.alertId) {
    await fetchAlertDetails(props.alertId)
  }
})

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
function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
}

function formatTimestamp(timestamp: string | Date): string {
  const date = new Date(timestamp)
  return new Intl.DateTimeFormat('de-DE', {
    dateStyle: 'medium',
    timeStyle: 'medium'
  }).format(date)
}

function getSeverityClass(severity?: string): string {
  const severityLower = severity?.toLowerCase()
  switch (severityLower) {
    case 'high':
      return 'text-destructive font-semibold'
    case 'medium':
      return 'text-orange-500 font-semibold'
    case 'low':
      return 'text-blue-500 font-semibold'
    default:
      return 'text-muted-foreground'
  }
}

// Match table severity styling for a consistent pill look
function getSeverityPillClass(severity?: string): string {
  const s = severity?.toLowerCase()
  const map: Record<string, string> = {
    high: 'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-primary text-primary-foreground',
    medium: 'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-accent text-accent-foreground',
    low: 'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-muted text-muted-foreground',
  }
  return map[s ?? ''] || map.low
}
</script>

<template>
  <Dialog v-model:open="dialogOpen">
    <DialogContent class="w-[min(100vw-2rem,1200px)] sm:max-w-5xl md:max-w-6xl max-h-[85vh] overflow-hidden flex flex-col">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          <Shield class="h-5 w-5 text-primary" />
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
        <div v-if="alertData" class="rounded-md border bg-muted/30 px-4 py-3 mb-4">
          <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div class="flex items-center gap-2 min-w-0">
              <span class="text-xs text-muted-foreground">Severity</span>
              <span :class="getSeverityPillClass(alertData.severity)">{{ alertData.severity?.toUpperCase() || 'UNKNOWN' }}</span>
            </div>
            <div class="flex items-center gap-2 min-w-0">
              <Clock class="h-4 w-4 text-muted-foreground" />
              <span class="truncate text-sm" :title="formatTimestamp(alertData.detected_at.timestamp)">
                {{ formatTimestamp(alertData.detected_at.timestamp) }}
              </span>
            </div>
            <div class="flex items-center gap-2 min-w-0">
              <Network class="h-4 w-4 text-muted-foreground" />
              <span class="text-xs text-muted-foreground">Src</span>
              <span class="font-mono text-sm truncate" :title="alertData.source?.address || 'Unknown'">
                {{ alertData.source?.address || 'Unknown' }}
              </span>
            </div>
            <div class="flex items-center gap-2 min-w-0">
              <Network class="h-4 w-4 text-muted-foreground" />
              <span class="text-xs text-muted-foreground">Dst</span>
              <span class="font-mono text-sm truncate" :title="alertData.target?.address || 'Unknown'">
                {{ alertData.target?.address || 'Unknown' }}
              </span>
            </div>
            <div class="flex items-center gap-2 min-w-0 sm:col-span-2 lg:col-span-1">
              <span class="text-xs text-muted-foreground">Message</span>
              <span class="font-mono text-sm break-all">{{ alertData.message_id }}</span>
              <Button
                variant="ghost"
                size="sm"
                class="h-6 w-6 p-0 shrink-0"
                @click="copyToClipboard(alertData.message_id)"
                :title="'Copy message id'"
              >
                <Copy class="h-3 w-3" />
              </Button>
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
            <AlertTriangle class="h-12 w-12 text-destructive mx-auto" />
            <p class="text-sm text-destructive">{{ error }}</p>
          </div>
        </div>

        <!-- Alert content -->
        <div v-else-if="alertData" class="space-y-6">
          <!-- Tabs for different sections -->
          <Tabs v-model:model-value="activeTab" class="w-full">
            <TabsList class="grid w-full grid-cols-2 sm:grid-cols-3 md:grid-cols-5">
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
                          @click="copyToClipboard(alertData.message_id)"
                          :title="'Copy message id'"
                        >
                          <Copy class="h-3 w-3" />
                        </Button>
                      </span>
                    </div>
                  </CardContent>
                </Card>

                <!-- Timestamps -->
                <Card>
                  <CardHeader class="pb-3">
                    <CardTitle class="text-sm font-medium flex items-center gap-2">
                      <Clock class="h-4 w-4" />
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
                      <Network class="h-4 w-4" />
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
                            @click="copyToClipboard(alertData.source.address)"
                            :title="'Copy source IP'"
                          >
                            <Copy class="h-3 w-3" />
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
                      <Network class="h-4 w-4" />
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
                            @click="copyToClipboard(alertData.target.address)"
                            :title="'Copy target IP'"
                          >
                            <Copy class="h-3 w-3" />
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
            <TabsContent value="analyzers" class="space-y-4 mt-4">
              <Card v-for="(analyzer, idx) in alertData.analyzers" :key="idx">
                <CardHeader class="pb-3">
                  <CardTitle class="text-sm font-medium flex items-center gap-2">
                    <Server class="h-4 w-4" />
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
            </TabsContent>

            <!-- References Tab -->
            <TabsContent value="references" class="space-y-4 mt-4">
              <Card v-if="alertData.references.length > 0">
                <CardHeader class="pb-3">
                  <CardTitle class="text-sm font-medium flex items-center gap-2">
                    <FileText class="h-4 w-4" />
                    References
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div class="space-y-2">
                    <div v-for="(ref, idx) in alertData.references" :key="idx" class="flex items-start gap-2">
                      <ExternalLink class="h-4 w-4 mt-0.5 text-muted-foreground" />
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
                        <span v-if="ref.origin" class="text-sm text-muted-foreground ml-2">
                          ({{ ref.origin }})
                        </span>
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
                    <Globe class="h-4 w-4" />
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
                    <div v-for="(value, key) in alertData.additional_data" :key="key" class="grid grid-cols-[180px_1fr] gap-x-4 gap-y-2 text-sm">
                      <span class="font-mono text-muted-foreground break-all">{{ key }}</span>
                      <span class="break-words">{{ value }}</span>
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

      <DialogFooter class="mt-4">
        <Button variant="outline" @click="dialogOpen = false">
          Close
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

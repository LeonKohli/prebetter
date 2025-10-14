<script setup lang="ts">
import type { GroupedAlertDetail } from '@/types/alerts'

interface Props {
  classifications: GroupedAlertDetail[]
  sourceIp: string
  targetIp: string
  maxVisible?: number
}

const props = withDefaults(defineProps<Props>(), {
  maxVisible: 5
})

const urlState = useNavigableUrlState()
const expanded = ref(false)

// Sort classifications by count (desc), then by name for stability
const sortedClassifications = computed(() => {
  const list = props.classifications ? [...props.classifications] : []
  return list.sort((a, b) => {
    if (b.count !== a.count) return b.count - a.count
    return (a.classification || '').localeCompare(b.classification || '')
  })
})

// Compute visible and hidden classifications from the sorted list
const visibleClassifications = computed(() =>
  expanded.value ? sortedClassifications.value : sortedClassifications.value.slice(0, props.maxVisible)
)

const hiddenCount = computed(() =>
  Math.max(0, (props.classifications?.length || 0) - props.maxVisible)
)

const showExpandButton = computed(() =>
  (props.classifications?.length || 0) > props.maxVisible
)

// Emphasis logic: compute relative magnitude and map to visual levels
const maxCount = computed(() => {
  if (!props.classifications?.length) return 0
  return props.classifications.reduce((m, c) => Math.max(m, c.count || 0), 0)
})

function getCountLevel(count: number): 'high' | 'medium' | 'low' {
  const max = Math.max(1, maxCount.value)
  const ratio = count / max
  if (ratio >= 0.66) return 'high'
  if (ratio >= 0.33) return 'medium'
  return 'low'
}

function getCountPillClass(count: number): string {
  const level = getCountLevel(count)
  const base = 'inline-flex items-center justify-center min-w-[1.5rem] h-5 px-1.5 rounded '
  if (level === 'high') return base + 'bg-primary text-primary-foreground text-xs font-semibold shadow-xs'
  if (level === 'medium') return base + 'bg-accent text-accent-foreground text-xs font-medium'
  return base + 'bg-muted text-muted-foreground text-[11px] font-medium'
}

function handleClassificationClick(classification: string) {
  urlState.navigateToDetails({
    sourceIp: props.sourceIp,
    targetIp: props.targetIp,
    classification
  })
}

function toggleExpanded() {
  expanded.value = !expanded.value
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-1.5">
    <button
      v-for="(alert, index) in visibleClassifications"
      :key="`${alert.classification}-${index}`"
      @click="handleClassificationClick(alert.classification)"
      class="inline-flex items-center gap-1.5 px-2 py-1 text-xs font-medium rounded-md bg-primary/10 text-primary hover:bg-primary/20 transition-colors border border-primary/20 cursor-pointer"
      :title="`${alert.classification} - Click to view details`"
      :aria-label="`${alert.classification}: ${alert.count} occurrences. Click to view details`"
    >
      <span class="truncate max-w-[200px]">{{ alert.classification }}</span>
      <span class="flex-shrink-0" :class="getCountPillClass(alert.count)" :title="`${alert.count} occurrences`">{{ alert.count }}</span>
    </button>

    <button
      v-if="showExpandButton && !expanded"
      @click="toggleExpanded"
      class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md bg-muted hover:bg-muted/80 text-muted-foreground transition-colors border border-border cursor-pointer"
      :title="`Show ${hiddenCount} more classification${hiddenCount > 1 ? 's' : ''}`"
    >
      <Icon name="lucide:chevron-down" class="h-3 w-3" />
      <span>+{{ hiddenCount }} more</span>
    </button>

    <button
      v-if="showExpandButton && expanded"
      @click="toggleExpanded"
      class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md bg-muted hover:bg-muted/80 text-muted-foreground transition-colors border border-border cursor-pointer"
      title="Show less"
    >
      <Icon name="lucide:chevron-up" class="h-3 w-3" />
      <span>Show less</span>
    </button>
  </div>
</template>

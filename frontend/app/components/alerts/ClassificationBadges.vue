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

// Compute visible and hidden classifications
const visibleClassifications = computed(() =>
  expanded.value ? props.classifications : props.classifications.slice(0, props.maxVisible)
)

const hiddenCount = computed(() =>
  Math.max(0, props.classifications.length - props.maxVisible)
)

const showExpandButton = computed(() =>
  props.classifications.length > props.maxVisible
)

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
    >
      <span class="truncate max-w-[200px]">{{ alert.classification }}</span>
      <span class="flex-shrink-0 font-bold">{{ alert.count }}</span>
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

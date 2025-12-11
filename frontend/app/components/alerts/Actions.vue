<script setup lang="ts">
const props = defineProps<{
  alert: AlertListItem | FlattenedGroupedAlert | CompactGroupedAlert
  isGrouped: boolean
}>()

const emit = defineEmits<{
  viewDetails: [alertId: string]
  requestDeleteSingle: [alert: AlertListItem]
  requestDeleteGroup: [alert: FlattenedGroupedAlert | CompactGroupedAlert]
}>()

const urlState = useNavigableUrlState()
const route = useRoute()
const router = useRouter()

function copyId() {
  let id = ''
  if (props.isGrouped) {
    // For grouped rows, use the IP pair as identifier (works for both legacy and compact)
    const src = props.alert.source_ipv4 ?? 'unknown'
    const dst = props.alert.target_ipv4 ?? 'unknown'
    id = `${src}-${dst}`
  } else if ('id' in props.alert) {
    id = props.alert.id
  }
  navigator.clipboard.writeText(id || '')
}

function handleViewDetails() {
  // For ungrouped view, use the alert ID directly
  if (!props.isGrouped && 'id' in props.alert) {
    emit('viewDetails', props.alert.id)
  }
}

const deleteLabel = computed(() => (props.isGrouped ? 'Delete IP pair' : 'Delete alert'))

function handleDelete() {
  // 'id' property only exists on AlertListItem - proper discriminant
  if ('id' in props.alert) {
    emit('requestDeleteSingle', props.alert)
  } else {
    emit('requestDeleteGroup', props.alert)
  }
}

async function viewAllForPair() {
  const sourceIp = props.alert.source_ipv4
  const targetIp = props.alert.target_ipv4

  if (!sourceIp || !targetIp) return

  const currentFilters = urlState.filters.value
  const { classification_text, ...rest } = currentFilters

  await router.push({
    query: {
      ...route.query,
      view: 'ungrouped',
      page: '1',
      size: '100',
      sort: 'detected_at:desc',
      filter: JSON.stringify({
        ...rest,
        source_ipv4: sourceIp,
        target_ipv4: targetIp,
      }),
    },
  })
}
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button
        variant="ghost"
        size="icon"
        class="size-8 p-0 text-muted-foreground hover:text-foreground"
        aria-label="Open actions menu"
      >
        <Icon name="lucide:more-horizontal" class="size-4" />
        <span class="sr-only">Open menu</span>
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end">
      <DropdownMenuLabel>Actions</DropdownMenuLabel>
      <DropdownMenuSeparator />
      <DropdownMenuItem v-if="!isGrouped" @click="handleViewDetails">
        <Icon name="lucide:file-text" class="mr-2 size-4" />
        View details
      </DropdownMenuItem>
      <DropdownMenuItem @click="viewAllForPair">
        <Icon name="lucide:list" class="mr-2 size-4" />
        View all from IP pair
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem class="text-destructive focus:text-destructive focus:bg-destructive/10" @click="handleDelete">
        <Icon name="lucide:trash-2" class="mr-2 size-4" />
        {{ deleteLabel }}
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem @click="copyId">
        <Icon name="lucide:copy" class="mr-2 size-4" />
        Copy {{ isGrouped ? 'IP pair' : 'alert ID' }}
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>

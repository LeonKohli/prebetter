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
    const anyAlert = props.alert as any
    const src = anyAlert?.source_ipv4 || 'unknown'
    const dst = anyAlert?.target_ipv4 || 'unknown'
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
  if (props.isGrouped) {
    emit('requestDeleteGroup', props.alert as FlattenedGroupedAlert | CompactGroupedAlert)
  } else if ('id' in props.alert) {
    emit('requestDeleteSingle', props.alert as AlertListItem)
  }
}

async function viewAllForPair() {
  const anyAlert = props.alert as any
  const sourceIp = anyAlert?.source_ipv4
  const targetIp = anyAlert?.target_ipv4

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
      <Button variant="ghost" class="h-8 w-8 p-0">
        <span class="sr-only">Open menu</span>
        <Icon name="lucide:more-horizontal" class="h-4 w-4" />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end">
      <DropdownMenuLabel>Actions</DropdownMenuLabel>
      <DropdownMenuItem v-if="!isGrouped" @click="handleViewDetails">
        <Icon name="lucide:file-text" class="mr-2 h-4 w-4" />
        View details
      </DropdownMenuItem>
      <DropdownMenuItem @click="viewAllForPair">
        <Icon name="lucide:list" class="mr-2 h-4 w-4" />
        View all from IP pair
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem class="text-destructive focus:text-destructive focus:bg-destructive/10" @click="handleDelete">
        <Icon name="lucide:trash-2" class="mr-2 h-4 w-4" />
        {{ deleteLabel }}
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem @click="copyId">
        <Icon name="lucide:copy" class="mr-2 h-4 w-4" />
        Copy {{ isGrouped ? 'IP pair' : 'alert ID' }}
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>

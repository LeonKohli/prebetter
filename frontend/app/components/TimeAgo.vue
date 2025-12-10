<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'

const props = defineProps<{
  time: string | Date | number
}>()

// useTimeAgo handles reactivity internally with 30s default interval
// rounding: 'floor' ensures "48 min ago" not "1 hour ago"
const timeAgo = useTimeAgo(() => props.time, {
  rounding: 'floor',
})
</script>

<template>
  <span data-allow-mismatch>{{ timeAgo }}</span>
</template>

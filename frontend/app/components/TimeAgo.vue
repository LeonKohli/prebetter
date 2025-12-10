<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'

const props = defineProps<{
  time: string | Date | number
}>()

// useTimeAgo handles reactivity internally with 30s default interval
const timeAgo = useTimeAgo(() => props.time)
</script>

<template>
  <span data-allow-mismatch>{{ timeAgo }}</span>
</template>

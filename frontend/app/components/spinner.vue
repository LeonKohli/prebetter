<script setup lang="ts">
interface Props {
  class?: string
}

const props = defineProps<Props>()
</script>

<template>
  <div
    :class="[
      'inline-block animate-spin rounded-full border-2 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]',
      props.class
    ]"
    role="status"
  >
    <span class="sr-only">Loading...</span>
  </div>
</template>
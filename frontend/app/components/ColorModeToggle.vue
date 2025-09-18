<template>
  <Button
    variant="ghost"
    size="icon"
    :aria-label="label"
    @click="toggle"
    class="transition-all duration-200 hover:scale-105"
  >
    <Icon :name="icon" class="w-5 h-5 transition-all duration-300 ease-in-out" />
  </Button>
</template>

<script setup lang="ts">
const colorMode = useColorMode()

const icon = computed(() => {
  // Always show icon based on what's actually displayed
  return colorMode.value === 'dark' ? 'lucide:moon' : 'lucide:sun'
})

const label = computed(() => {
  return colorMode.value === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'
})

function toggle() {
  // When toggling, we need to handle the system preference case
  // If preference is system, toggle based on current value
  // Otherwise toggle between light and dark

  if (colorMode.preference === 'system') {
    // User is on system preference, toggle to opposite of current value
    colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
  } else {
    // User has explicit preference, toggle it
    colorMode.preference = colorMode.preference === 'dark' ? 'light' : 'dark'
  }
}
</script>
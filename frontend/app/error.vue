<script setup lang="ts">
import type { NuxtError } from '#app'

const props = defineProps({
  error: Object as () => NuxtError
})

const handleError = () => clearError({ redirect: '/' })

// Determine the error message and title based on status code
const errorTitle = computed(() => {
  if (props.error?.statusCode === 404) {
    return 'Page not found'
  }
  if (props.error?.statusCode === 403) {
    return 'Access denied'
  }
  if (props.error?.statusCode === 500) {
    return 'Server error'
  }
  return 'An error occurred'
})

const errorMessage = computed(() => {
  if (props.error?.statusMessage) {
    return props.error.statusMessage
  }
  if (props.error?.statusCode === 404) {
    return "Sorry, the page you're looking for doesn't exist."
  }
  if (props.error?.statusCode === 403) {
    return "You don't have permission to access this resource."
  }
  if (props.error?.statusCode === 500) {
    return 'Something went wrong on our end. Please try again later.'
  }
  return 'Something unexpected happened. Please try again.'
})
</script>

<template>
    <div class="min-h-screen flex items-center justify-center px-4 py-16">
      <div class="w-full max-w-md space-y-8 text-center">
        <!-- Error status code -->
        <div class="space-y-2">
          <h1 class="text-7xl font-bold tracking-tighter text-muted-foreground/20">
            {{ error?.statusCode || '500' }}
          </h1>
          <h2 class="text-3xl font-bold tracking-tight">
            {{ errorTitle }}
          </h2>
        </div>

        <!-- Error message -->
        <p class="text-muted-foreground text-lg">
          {{ errorMessage }}
        </p>

        <!-- Action buttons -->
        <div class="flex flex-col sm:flex-row gap-4 justify-center pt-4">
          <Button
            @click="handleError"
            size="lg"
            class="min-w-[140px]"
          >
            <Icon name="lucide:home" class="mr-2 h-4 w-4" />
            Go home
          </Button>
          <Button
            @click="$router.back()"
            variant="outline"
            size="lg"
            class="min-w-[140px]"
          >
            <Icon name="lucide:arrow-left" class="mr-2 h-4 w-4" />
            Go back
          </Button>
        </div>
      </div>
    </div>

</template>
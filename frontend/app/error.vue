<script setup lang="ts">
import type { NuxtError } from '#app'

// FastAPI validation error format
interface ValidationError {
  loc: (string | number)[]
  msg: string
  type: string
}

// FastAPI error data format
interface FastAPIErrorData {
  detail?: string | ValidationError[]
}

const props = defineProps({
  error: Object as () => NuxtError<FastAPIErrorData>
})

const router = useRouter()
const isDev = process.dev

const codeContainer = ref<HTMLElement | null>(null)

const handleError = () => clearError({ redirect: '/' })
const goBack = () => router.back()

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
  const detail = props.error?.data?.detail
  if (detail) {
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail)) {
      // Format FastAPI validation errors
      return detail
        .map(
          (err: ValidationError) =>
            `${err.loc.slice(1).join(' → ')}: ${
              err.msg || 'Invalid value'
            }`,
        )
        .join('\n')
    }
  }

  if (props.error?.message && props.error.message !== props.error.statusMessage) {
    return props.error.message
  }

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

function selectCode() {
  const pre = codeContainer.value?.querySelector('pre')
  if (pre) {
    const selection = window.getSelection()
    if (selection) {
      const range = document.createRange()
      range.selectNodeContents(pre)
      selection.removeAllRanges()
      selection.addRange(range)
    }
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-background px-4">
    <div class="w-full max-w-md space-y-6 text-center">
      <div class="space-y-2">
        <h1
          class="text-7xl font-bold tracking-tighter text-muted-foreground/20"
        >
          {{ error?.statusCode || '500' }}
        </h1>
        <h2 class="text-3xl font-bold tracking-tight">
          {{ errorTitle }}
        </h2>
      </div>

      <p class="whitespace-pre-line text-muted-foreground text-lg">
        {{ errorMessage }}
      </p>

      <div class="flex flex-col gap-4 justify-center pt-4 sm:flex-row">
        <Button @click="handleError" size="lg" class="min-w-[140px]">
          <Icon name="lucide:home" class="mr-2 h-4 w-4" />
          Go home
        </Button>
        <Button
          @click="goBack"
          variant="outline"
          size="lg"
          class="min-w-[140px]"
        >
          <Icon name="lucide:arrow-left" class="mr-2 h-4 w-4" />
          Go back
        </Button>
      </div>

      <div v-if="isDev" class="pt-8 w-full">
        <p class="font-bold text-left">
          Developer Information
        </p>
        <div
          ref="codeContainer"
          tabindex="0"
          class="mt-2 cursor-pointer overflow-x-auto rounded-md bg-muted p-4 text-left text-xs focus:outline-none focus:ring-2 focus:ring-ring"
          @click="selectCode"
          @keydown.ctrl.a.prevent="selectCode"
          @keydown.meta.a.prevent="selectCode"
        >
          <pre><code>{{ JSON.stringify(error, null, 2) }}</code></pre>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'
import { cn } from '@/utils/utils'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()

const attrs = useAttrs()
const model = defineModel<string | number>()
const showPassword = ref(false)
</script>

<template>
  <div :class="cn('relative', props.class)">
    <Input
      v-model="model"
      v-bind="attrs"
      :type="showPassword ? 'text' : 'password'"
      class="pr-10"
    />
    <Button
      type="button"
      variant="ghost"
      size="icon"
      class="absolute inset-y-0 right-0 my-auto mr-1 h-8 w-8 text-muted-foreground"
      :aria-pressed="showPassword"
      @click="showPassword = !showPassword"
    >
      <EyeOff v-if="showPassword" class="h-4 w-4" aria-hidden="true" />
      <Eye v-else class="h-4 w-4" aria-hidden="true" />
      <span class="sr-only">{{ showPassword ? 'Hide password' : 'Show password' }}</span>
    </Button>
  </div>
</template>

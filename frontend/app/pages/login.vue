<template>
  <div class="flex min-h-screen items-center justify-center bg-background px-4">
    <div class="w-full max-w-sm space-y-6">
      <div class="space-y-2 text-center">
        <span class="text-xs font-medium uppercase tracking-wide text-primary/80">Prebetter</span>
        <h1 class="text-2xl font-semibold tracking-tight text-foreground">Prebetter Login</h1>
        <p class="text-sm text-muted-foreground">Sign in to access your security dashboard.</p>
      </div>

      <Card>
        <CardHeader class="space-y-1">
          <CardTitle class="text-lg font-semibold tracking-tight">Sign in</CardTitle>
          <CardDescription>Enter your credentials to continue.</CardDescription>
        </CardHeader>
        <CardContent>
          <Form :validation-schema="formSchema" :initial-values="initialValues" v-slot="{ handleSubmit, isSubmitting }">
            <form class="grid gap-4" @submit.prevent="handleSubmit(submitLoginHandler)">
              <Alert v-if="authError" variant="destructive">
                <AlertTriangle class="h-4 w-4" aria-hidden="true" />
                <AlertTitle>Unable to sign in</AlertTitle>
                <AlertDescription>
                  {{ authError }}
                </AlertDescription>
              </Alert>

              <FormField v-slot="{ componentField }" name="username">
                <FormItem>
                  <FormLabel>Username</FormLabel>
                  <FormControl>
                    <Input
                      v-bind="componentField"
                      placeholder="your.username"
                      autocomplete="username"
                      autofocus
                      :disabled="isSubmitting"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              </FormField>

              <FormField v-slot="{ componentField }" name="password">
                <FormItem>
                  <FormLabel>Password</FormLabel>
                  <FormControl>
                    <div class="relative">
                      <Input
                        v-bind="componentField"
                        :type="showPassword ? 'text' : 'password'"
                        placeholder="••••••••"
                        autocomplete="current-password"
                        :disabled="isSubmitting"
                        class="pr-10"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        class="absolute inset-y-0 right-0 my-auto mr-1 h-8 w-8 text-muted-foreground"
                        @click="togglePasswordVisibility"
                        :aria-pressed="showPassword"
                        :disabled="isSubmitting"
                      >
                        <EyeOff v-if="showPassword" class="h-4 w-4" aria-hidden="true" />
                        <Eye v-else class="h-4 w-4" aria-hidden="true" />
                        <span class="sr-only">
                          {{ showPassword ? 'Hide password' : 'Show password' }}
                        </span>
                      </Button>
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              </FormField>

              <Button type="submit" class="w-full" :disabled="isSubmitting">
                <Icon v-if="isSubmitting" name="lucide:loader-2" class="mr-2 size-4 animate-spin" />
                {{ isSubmitting ? 'Signing in…' : 'Sign in' }}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { AlertTriangle, Eye, EyeOff } from 'lucide-vue-next'
import { toTypedSchema } from '@vee-validate/zod'
import type { SubmissionContext, SubmissionHandler } from 'vee-validate'
import type { z } from 'zod'
import { Form } from '@/components/ui/form'
import { loginSchema } from '@/utils/validation'

definePageMeta({
  layout: false,
  guestOnly: true,
})

useHead({
  title: 'Sign in · Prebetter',
})

const session = useUserSession()
const route = useRoute()

type LoginFormValues = z.infer<typeof loginSchema>

const formSchema = toTypedSchema(loginSchema)
const initialValues: LoginFormValues = {
  username: '',
  password: '',
}

const authError = ref('')
const showPassword = ref(false)

const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value
}

const submitLogin: SubmissionHandler<LoginFormValues> = async (
  values,
  { setFieldError }: SubmissionContext<LoginFormValues>,
) => {
  authError.value = ''

  try {
    await $fetch('/api/auth/login', {
      method: 'POST',
      body: {
        username: values.username.trim(),
        password: values.password,
      },
    })

    await session.fetch()

    const redirect =
      typeof route.query.redirect === 'string' && route.query.redirect.trim().length > 0
        ? route.query.redirect
        : '/'

    try {
      await navigateTo(redirect, { replace: true })
    } catch {
      window.location.href = redirect
    }
  } catch (error: any) {
    console.error('Login error:', error)
    const fetchError = error as { data?: { message?: string; detail?: string }; statusMessage?: string }
    const message =
      fetchError?.data?.message ||
      fetchError?.data?.detail ||
      fetchError?.statusMessage ||
      'Invalid username or password. Please try again.'
    authError.value = message
    setFieldError('password', 'Check your credentials and try again.')
  }
}

const submitLoginHandler = submitLogin as SubmissionHandler
</script>

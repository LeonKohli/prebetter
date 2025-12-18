<template>
  <div class="flex min-h-screen items-center justify-center bg-background px-4">
    <div class="w-full max-w-sm space-y-6">
      <div class="space-y-2 text-center">
        <span class="font-display text-xs font-medium uppercase tracking-wider text-primary/80">Prebetter</span>
        <h1 class="font-display text-3xl font-bold text-foreground">Prebetter Login</h1>
        <p class="text-sm text-muted-foreground">Sign in to access your security dashboard.</p>
      </div>

      <Card>
        <CardHeader class="space-y-1">
          <CardTitle class="text-lg font-semibold tracking-tight">Sign in</CardTitle>
          <CardDescription>Enter your credentials to continue.</CardDescription>
        </CardHeader>
        <CardContent>
          <form @submit="onSubmit">
            <div class="grid gap-4">
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
                      placeholder="Username"
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
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { AlertTriangle, Eye, EyeOff } from 'lucide-vue-next'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'

definePageMeta({
  layout: false,
  guestOnly: true,
})

useHead({
  title: 'Sign in · Prebetter',
})

const session = useUserSession()
const route = useRoute()

const authError = ref('')
const showPassword = ref(false)

const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value
}

// Form setup with useForm - the canonical vee-validate pattern
const form = useForm({
  validationSchema: toTypedSchema(loginSchema),
  initialValues: {
    username: '',
    password: '',
  },
})

const { isSubmitting, setFieldError } = form

// handleSubmit returns a properly typed submit handler
const onSubmit = form.handleSubmit(async (values) => {
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

    // Validate redirect to prevent open redirect attacks
    // Pattern from Nuxt Content Studio - only allow safe relative paths
    const rawRedirect = route.query.redirect
    let redirect = '/'
    if (typeof rawRedirect === 'string' && rawRedirect.startsWith('/') && !rawRedirect.startsWith('//')) {
      redirect = rawRedirect
    }

    await navigateTo(redirect, { replace: true })
  } catch (error) {
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
})
</script>

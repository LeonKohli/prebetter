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
                    <PasswordInput
                      v-bind="componentField"
                      placeholder="••••••••"
                      autocomplete="current-password"
                      :disabled="isSubmitting"
                    />
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
import { AlertTriangle } from '@lucide/vue'
import { toFormValidator } from '@vee-validate/zod'
import { useForm } from 'vee-validate'

definePageMeta({
  layout: false,
  guestOnly: true,
})

useHead({
  title: 'Sign in · Prebetter',
})

const route = useRoute()

const authError = ref('')

// Form setup with useForm - the canonical vee-validate pattern
const form = useForm({
  validationSchema: toFormValidator(loginSchema),
  initialValues: {
    username: '',
    password: '',
  },
})

const { isSubmitting, setFieldError } = form

// handleSubmit returns a properly typed submit handler
const onSubmit = form.handleSubmit(async (values) => {
  authError.value = ''

  const { error } = await authClient.signIn.username({
    username: values.username.trim(),
    password: values.password,
  })

  if (error) {
    authError.value = error.message || 'Invalid username or password. Please try again.'
    setFieldError('password', 'Check your credentials and try again.')
    return
  }

  // Validate redirect to prevent open redirect attacks
  // Pattern from Nuxt Content Studio - only allow safe relative paths
  const rawRedirect = route.query.redirect
  let redirect = '/'
  if (typeof rawRedirect === 'string' && rawRedirect.startsWith('/') && !rawRedirect.startsWith('//')) {
    redirect = rawRedirect
  }

  await navigateTo(redirect, { replace: true })
})
</script>

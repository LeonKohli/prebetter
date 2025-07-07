<template>
  <div class="flex min-h-screen items-center justify-center">
    <Card class="w-full max-w-md">
      <CardHeader>
        <CardTitle>Login to Prebetter</CardTitle>
        <CardDescription>
          Enter your credentials to access the SIEM dashboard
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form @submit.prevent="handleLogin" class="space-y-4">
          <div class="space-y-2">
            <label for="username" class="text-sm font-medium">Username</label>
            <Input
              id="username"
              v-model="username"
              type="text"
              placeholder="Enter your username"
              required
              :disabled="loading"
            />
          </div>
          
          <div class="space-y-2">
            <label for="password" class="text-sm font-medium">Password</label>
            <Input
              id="password"
              v-model="password"
              type="password"
              placeholder="Enter your password"
              required
              :disabled="loading"
            />
          </div>

          <div v-if="infoMsg" class="rounded-md bg-muted p-3">
            <p class="text-sm text-muted-foreground">{{ infoMsg }}</p>
          </div>

          <div v-if="errorMsg" class="rounded-md bg-destructive/10 p-3">
            <p class="text-sm text-destructive">{{ errorMsg }}</p>
          </div>

          <Button type="submit" class="w-full" :disabled="loading">
            <Icon v-if="loading" name="lucide:loader-2" class="mr-2 size-4 animate-spin" />
            {{ loading ? 'Logging in...' : 'Login' }}
          </Button>
        </form>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: false,
  guestOnly: true, // Only accessible when not logged in
})

const session = useUserSession()
const route = useRoute()
const username = ref('')
const password = ref('')
const errorMsg = ref<string | null>(null)
const infoMsg = ref<string | null>(null)
const loading = ref(false)

// Handle reason messages
onMounted(() => {
  const reason = route.query.reason as string
  if (reason === 'session-expired') {
    infoMsg.value = 'Your session has expired. Please log in again.'
  } else if (reason === 'unauthorized') {
    infoMsg.value = 'Please log in to continue.'
  }
})

async function handleLogin() {
  errorMsg.value = null
  loading.value = true
  
  try {
    await $fetch('/api/auth/login', {
      method: 'POST',
      body: {
        username: username.value,
        password: password.value,
      },
    })
    
    // Refetch the session to update the UI
    await session.fetch()

    // Redirect to original page or dashboard
    const redirect = route.query.redirect as string || '/'
    await navigateTo(redirect)
  } catch (error: any) {
    errorMsg.value = error.data?.statusMessage || 'An error occurred.'
  } finally {
    loading.value = false
  }
}

// Redirect if already logged in
if (session.loggedIn.value) {
  navigateTo('/')
}
</script>
<template>
  <div class="flex min-h-screen items-center justify-center">
    <Card class="w-full max-w-md">
      <CardHeader>
        <CardTitle>Login to Prebetter</CardTitle>
        <CardDescription>
          Enter your credentials to access the IDS dashboard
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
const loading = ref(false)


async function handleLogin() {
  loading.value = true
  
  try {
    const result = await $fetch('/api/auth/login', {
      method: 'POST',
      body: {
        username: username.value,
        password: password.value,
      },
    })
    
    console.log('Login successful:', result)
    
    // Refetch the session to update the UI
    await session.fetch()
    
    console.log('Session fetched, redirecting...')

    // Redirect to original page or dashboard
    const redirect = route.query.redirect as string || '/'
    console.log('Redirecting to:', redirect)
    
    // Use window.location as fallback if navigateTo fails
    try {
      await navigateTo(redirect)
    } catch {
      window.location.href = redirect
    }
  } catch (error: any) {
    console.error('Login error:', error)
  } finally {
    loading.value = false
  }
}
</script>
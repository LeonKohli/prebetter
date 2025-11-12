<template>
  <div class="h-[calc(100vh-3rem)] px-2 md:px-4 pt-2 md:pt-4">
    <AuthState v-slot="{ loggedIn }">
      <div v-if="loggedIn" class="h-full">
        <AlertsTable />
      </div>
      
      <div v-else>
        <Card>
          <CardHeader>
            <CardTitle>Welcome to Prebetter IDS</CardTitle>
            <CardDescription>
              Intrusion Detection System Dashboard
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p class="mb-4">
              Please log in to access the security dashboard and view alerts from your monitored systems.
            </p>
            <Button as-child>
              <NuxtLink to="/login">
                <Icon name="lucide:log-in" class="mr-2 size-4" />
                Log In
              </NuxtLink>
            </Button>
          </CardContent>
        </Card>
      </div>
    </AuthState>
  </div>
</template>

<script setup lang="ts">
import AlertsTable from '@/components/alerts/AlertsTable.vue'

definePageMeta({
  requiresAuth: true,
})

useSeoMeta({
  title: 'Security Alerts - Prebetter IDS',
  description: 'Real-time security alert monitoring and analysis dashboard',
})
</script>
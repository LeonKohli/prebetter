<template>
  <div class="h-[calc(100vh-3rem)] p-2 md:p-4">
    <AuthState v-slot="{ loggedIn }">
      <div v-if="loggedIn" class="h-full">
        <!-- Main alerts table -->
        <AlertsTable />
      </div>
      
      <div v-else>
        <!-- Welcome message for non-authenticated users -->
        <Card>
          <CardHeader>
            <CardTitle>Welcome to Prebetter SIEM</CardTitle>
            <CardDescription>
              Security Information and Event Management Dashboard
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

// SEO
useSeoMeta({
  title: 'Security Alerts - Prebetter SIEM',
  description: 'Real-time security alert monitoring and analysis dashboard',
})
</script>
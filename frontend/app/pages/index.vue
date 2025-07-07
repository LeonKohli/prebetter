<template>
  <div class="container mx-auto px-4 py-8">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold mb-2">Security Dashboard</h1>
      <p class="text-muted-foreground">
        Monitor and analyze security alerts from your Prelude IDS system
      </p>
    </div>

    <AuthState v-slot="{ loggedIn, user }">
      <div v-if="loggedIn">
        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">Total Alerts</CardTitle>
              <Icon name="lucide:alert-circle" class="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold">0</div>
              <p class="text-xs text-muted-foreground">
                Last 24 hours
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">High Severity</CardTitle>
              <Icon name="lucide:alert-triangle" class="size-4 text-destructive" />
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold">0</div>
              <p class="text-xs text-muted-foreground">
                Requires immediate attention
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">Medium Severity</CardTitle>
              <Icon name="lucide:info" class="size-4 text-yellow-600" />
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold">0</div>
              <p class="text-xs text-muted-foreground">
                Monitor closely
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">Active Analyzers</CardTitle>
              <Icon name="lucide:activity" class="size-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold">0</div>
              <p class="text-xs text-muted-foreground">
                Currently online
              </p>
            </CardContent>
          </Card>
        </div>

        <!-- Welcome Card -->
        <Card>
          <CardHeader>
            <CardTitle>Welcome, {{ user?.username || 'User' }}!</CardTitle>
            <CardDescription>
              You are successfully logged in to the Prebetter SIEM Dashboard.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p class="text-muted-foreground">
              This is a static demo page. In a real implementation, this dashboard would show:
            </p>
            <ul class="mt-4 space-y-2 text-sm text-muted-foreground">
              <li class="flex items-start gap-2">
                <Icon name="lucide:check" class="size-4 text-green-600 mt-0.5" />
                <span>Real-time security alerts from your Prelude IDS system</span>
              </li>
              <li class="flex items-start gap-2">
                <Icon name="lucide:check" class="size-4 text-green-600 mt-0.5" />
                <span>Alert statistics and trends</span>
              </li>
              <li class="flex items-start gap-2">
                <Icon name="lucide:check" class="size-4 text-green-600 mt-0.5" />
                <span>System health and analyzer status</span>
              </li>
              <li class="flex items-start gap-2">
                <Icon name="lucide:check" class="size-4 text-green-600 mt-0.5" />
                <span>Alert filtering and export capabilities</span>
              </li>
            </ul>
          </CardContent>
        </Card>
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
definePageMeta({
  requiresAuth: true,
})

// SEO
useSeoMeta({
  title: 'Dashboard - Prebetter SIEM',
  description: 'Security Information and Event Management Dashboard',
})
</script>
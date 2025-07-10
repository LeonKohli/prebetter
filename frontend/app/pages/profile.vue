<template>
  <div class="container mx-auto py-6">
    <h1 class="text-3xl font-bold mb-6">Profile</h1>
    
    <!-- User Info -->
    <Card class="mb-6">
      <CardHeader>
        <CardTitle>Your Information</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="space-y-2">
          <p><span class="font-medium">Username:</span> {{ user?.username }}</p>
          <p><span class="font-medium">Email:</span> {{ user?.email }}</p>
          <p><span class="font-medium">Full Name:</span> {{ user?.fullName || 'Not set' }}</p>
          <p><span class="font-medium">Role:</span> {{ user?.isSuperuser ? 'Administrator' : 'User' }}</p>
        </div>
      </CardContent>
    </Card>

    <!-- User List for Superusers -->
    <Card v-if="user?.isSuperuser">
      <CardHeader>
        <CardTitle>All Users</CardTitle>
      </CardHeader>
      <CardContent>
        <div v-if="pending">Loading...</div>
        <div v-else-if="error">Error: {{ error.message }}</div>
        <table v-else class="w-full">
          <thead>
            <tr class="border-b">
              <th class="text-left p-2">Username</th>
              <th class="text-left p-2">Email</th>
              <th class="text-left p-2">Full Name</th>
              <th class="text-left p-2">Role</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id" class="border-b">
              <td class="p-2">{{ u.username }}</td>
              <td class="p-2">{{ u.email }}</td>
              <td class="p-2">{{ u.full_name || '-' }}</td>
              <td class="p-2">{{ u.is_superuser ? 'Admin' : 'User' }}</td>
            </tr>
          </tbody>
        </table>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

// Require authentication to view this page
definePageMeta({
  requiresAuth: true
})

const { user } = await useUserSession()

// Define type for user list response
interface UserListResponse {
  items: Array<{
    id: number
    email: string
    username: string
    full_name?: string
    is_superuser: boolean
  }>
}

// Fetch users if superuser - must use trailing slash
const { data: response, pending, error } = user.value?.isSuperuser 
  ? await useFetch<UserListResponse>('/api/users')
  : { data: ref<UserListResponse | null>(null), pending: ref(false), error: ref(null) }

const users = computed(() => response.value?.items || [])
</script>
<template>
  <div class="container mx-auto py-6 space-y-6">
    <h1 class="text-3xl font-bold">Profile</h1>
    
    <Card>
      <CardHeader class="flex flex-row items-center justify-between">
        <CardTitle>Your Information</CardTitle>
        <div class="flex gap-2">
          <ProfileEditDialog 
            v-if="user" 
            :user="user" 
            @update:success="handleProfileUpdate"
          />
          <ProfileChangePasswordDialog @update:success="handlePasswordChanged" />
        </div>
      </CardHeader>
      <CardContent>
        <div class="space-y-2">
          <div class="flex items-center gap-2">
            <span class="font-medium text-muted-foreground">Username:</span>
            <span>{{ user?.username }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="font-medium text-muted-foreground">Email:</span>
            <span>{{ user?.email }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="font-medium text-muted-foreground">Full Name:</span>
            <span>{{ user?.full_name || 'Not set' }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="font-medium text-muted-foreground">Role:</span>
            <Badge :variant="user?.is_superuser ? 'default' : 'secondary'">
              {{ user?.is_superuser ? 'Administrator' : 'User' }}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>

    <Card v-if="user?.is_superuser">
      <CardHeader>
        <CardTitle>Administration</CardTitle>
        <CardDescription>
          Manage users and system settings
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ProfileUserManagementTable v-if="user" :current-user-id="user.id" />
      </CardContent>
    </Card>

    <Transition name="fade">
      <Alert v-if="alert" :variant="alert.variant" class="fixed bottom-4 right-4 w-auto max-w-md">
        <Icon :name="alert.icon" class="size-4" />
        <AlertTitle>{{ alert.title }}</AlertTitle>
        <AlertDescription v-if="alert.description">
          {{ alert.description }}
        </AlertDescription>
      </Alert>
    </Transition>
  </div>
</template>

<script setup lang="ts">

definePageMeta({
  requiresAuth: true
})

const session = useUserSession()
const { user } = session

interface AlertState {
  variant: 'default' | 'destructive'
  icon: string
  title: string
  description?: string
}

const alert = ref<AlertState | null>(null)
let alertTimeout: NodeJS.Timeout | null = null

const showAlert = (alertData: AlertState) => {
  alert.value = alertData
  
  if (alertTimeout) {
    clearTimeout(alertTimeout)
  }
  
  alertTimeout = setTimeout(() => {
    alert.value = null
  }, 5000)
}

const handleProfileUpdate = async () => {
  // Critical: Refresh session to sync navbar and permissions
  await session.fetch()
  
  showAlert({
    variant: 'default',
    icon: 'lucide:check-circle',
    title: 'Profile Updated',
    description: 'Your profile information has been successfully updated.',
  })
}

const handlePasswordChanged = () => {
  showAlert({
    variant: 'default',
    icon: 'lucide:check-circle',
    title: 'Password Changed',
    description: 'Your password has been successfully changed.',
  })
}

onUnmounted(() => {
  if (alertTimeout) {
    clearTimeout(alertTimeout)
  }
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: all 0.3s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
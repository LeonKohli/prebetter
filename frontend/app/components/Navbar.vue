<template>
  <header
    role="banner"
    class="sticky top-0 z-20 border-b backdrop-blur supports-backdrop-blur:bg-background/60 px-4 md:px-8"
  >
    <div class="max-w-8xl mx-auto h-16 flex items-center justify-between">
      <NuxtLink to="/" class="flex items-center space-x-3 group" aria-label="Home">
        <Icon name="lucide:shield-alert" class="h-8 w-8 text-primary" />
        <div>
          <span class="font-semibold text-lg tracking-tight">Prebetter</span>
          <p class="text-xs text-muted-foreground hidden md:block">SIEM Dashboard</p>
        </div>
      </NuxtLink>

      <div class="flex items-center space-x-4">
        <AuthState v-slot="{ loggedIn, user }">
          <div v-if="loggedIn && user" class="flex items-center space-x-4">
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button variant="ghost" class="flex items-center space-x-2">
                  <Icon name="lucide:user" class="size-4" />
                  <span class="hidden md:inline">{{ user.username }}</span>
                  <Icon name="lucide:chevron-down" class="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" class="w-56">
                <DropdownMenuLabel>
                  <div class="flex flex-col space-y-1">
                    <p class="text-sm font-medium">{{ user.fullName || user.username }}</p>
                    <p class="text-xs text-muted-foreground">{{ user.email }}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem v-if="user.isSuperuser" as-child>
                  <NuxtLink to="/admin">
                    <Icon name="lucide:settings" class="mr-2 size-4" />
                    Admin Settings
                  </NuxtLink>
                </DropdownMenuItem>
                <DropdownMenuItem @click="handleLogout">
                  <Icon name="lucide:log-out" class="mr-2 size-4" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          <div v-else>
            <Button as-child variant="default" size="sm">
              <NuxtLink to="/login">
                <Icon name="lucide:log-in" class="mr-2 size-4" />
                Login
              </NuxtLink>
            </Button>
          </div>
        </AuthState>
        
        <ClientOnly> 
          <ColorModeToggle />
          <template #fallback>
            <div class="w-10 h-10"></div>
          </template>
        </ClientOnly>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
const { clear } = useUserSession()
const router = useRouter()

const handleLogout = async () => {
  await $fetch('/api/auth/logout', {
    method: 'POST',
  }).catch(() => {
    // Ignore errors, we'll clear session anyway
  })
  
  await clear()
  await router.push('/login')
}
</script> 
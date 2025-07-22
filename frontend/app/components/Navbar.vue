<template>
  <header
    role="banner"
    class="sticky top-0 z-20 border-b backdrop-blur supports-backdrop-blur:bg-background/95 px-2 md:px-4"
  >
    <div class="h-12 flex items-center justify-between">
      <NuxtLink to="/" class="flex items-center space-x-2 group" aria-label="Home">
        <Icon name="lucide:shield-alert" class="h-5 w-5 text-primary" />
        <div class="flex items-baseline space-x-1">
          <span class="font-semibold text-sm tracking-tight">Prebetter</span>
          <span class="text-xs text-muted-foreground hidden lg:inline">SIEM</span>
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
                    <p class="text-sm font-medium">{{ user.full_name || user.username }}</p>
                    <p class="text-xs text-muted-foreground">{{ user.email }}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem as-child>
                  <NuxtLink to="/profile">
                    <Icon name="lucide:user" class="mr-2 size-4" />
                    View Profile
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
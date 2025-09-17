<template>
  <header
    role="banner"
    class="sticky top-0 z-20 border-b backdrop-blur supports-backdrop-blur:bg-background/95 px-2 md:px-4"
  >
    <AuthState v-slot="{ loggedIn, user }">
      <div class="h-12 flex items-center justify-between">
        <div class="flex items-center gap-6">
          <NuxtLink to="/" class="flex items-center space-x-2 group" aria-label="Home">
            <Icon name="lucide:shield-alert" class="h-5 w-5 text-primary" />
            <div class="flex items-baseline space-x-1">
              <span class="font-semibold text-sm tracking-tight">Prebetter</span>
              <span class="text-xs text-muted-foreground hidden lg:inline">IDS</span>
            </div>
          </NuxtLink>

          <nav v-if="loggedIn" class="hidden items-center gap-3 md:flex" aria-label="Main">
            <NuxtLink
              v-for="link in navLinks"
              :key="link.to"
              :to="link.to"
              :class="cn(
                'text-sm font-medium transition-colors hover:text-foreground',
                isActiveLink(link) ? 'text-foreground' : 'text-muted-foreground'
              )"
            >
              {{ link.label }}
            </NuxtLink>
          </nav>
        </div>

        <div class="flex items-center space-x-4">
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

          <ClientOnly>
            <ColorModeToggle />
            <template #fallback>
              <div class="w-10 h-10"></div>
            </template>
          </ClientOnly>
        </div>
      </div>
    </AuthState>
  </header>
</template>

<script setup lang="ts">
import { cn } from '@/utils/utils'

const { clear } = useUserSession()
const router = useRouter()
const route = useRoute()

const navLinks = [
  {
    to: '/',
    label: 'Alerts',
    match: (path: string) => path === '/',
  },
  {
    to: '/heartbeats',
    label: 'Heartbeats',
    match: (path: string) => path.startsWith('/heartbeats'),
  },
]

function isActiveLink(link: (typeof navLinks)[number]) {
  return link.match ? link.match(route.path) : route.path === link.to
}

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

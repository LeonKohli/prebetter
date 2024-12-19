<script setup lang="ts">
const colorMode = useColorMode()

const toggleTheme = () => {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}
</script>

<template>
    <div class="min-h-screen bg-background text-foreground">
        <header
            class="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div class="container-fluid px-4 sm:px-6 lg:px-8 flex items-center h-14 max-w-[2000px] mx-auto">
                <div class="flex mr-4">
                    <NuxtLink to="/" class="flex items-center mr-6 space-x-2">
                        <Icon name="lucide:shield-alert" class="w-6 h-6" />
                        <span class="hidden font-bold sm:inline-block">
                            Prelude SIEM
                        </span>
                    </NuxtLink>
                </div>
                <div class="flex items-center justify-between flex-1 space-x-2 md:justify-end">
                    <nav class="flex items-center">
                        <ClientOnly>
                            <Button variant="ghost" size="icon" @click="toggleTheme">
                                <Icon v-if="colorMode.value === 'dark'" name="lucide:sun" class="w-5 h-5" />
                                <Icon v-else name="lucide:moon" class="w-5 h-5" />
                            </Button>
                        </ClientOnly>
                    </nav>
                </div>
            </div>
        </header>

        <div class="flex-1">
            <slot />
        </div>

        <footer class="py-6 border-t md:py-0">
            <div class="container-fluid px-4 sm:px-6 lg:px-8 max-w-[2000px] mx-auto flex flex-col items-center justify-between gap-4 md:h-14 md:flex-row">
                <p class="text-sm leading-loose text-center text-muted-foreground md:text-left">
                    Built with Nuxt 4 and shadcn-vue
                </p>
            </div>
            
        </footer>
    </div>
</template> 
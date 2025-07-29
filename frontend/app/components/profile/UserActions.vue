<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button variant="ghost" size="sm" class="size-8 p-0">
        <Icon name="lucide:more-horizontal" class="size-4" />
        <span class="sr-only">Open menu</span>
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end">
      <DropdownMenuItem @click="$emit('edit', user)">
        <Icon name="lucide:edit" class="mr-2 size-4" />
        Edit
      </DropdownMenuItem>
      <DropdownMenuItem @click="$emit('resetPassword', user)">
        <Icon name="lucide:key" class="mr-2 size-4" />
        Reset Password
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem 
        @click="$emit('delete', user)"
        class="text-destructive"
        :disabled="user.id === currentUserId || (user.is_superuser && isLastSuperuser)"
      >
        <Icon name="lucide:trash" class="mr-2 size-4" />
        Delete
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>

<script setup lang="ts">
interface User {
  id: string
  username: string
  email: string
  full_name?: string | null
  is_superuser: boolean
  created_at: string
  updated_at?: string | null
}

interface Props {
  user: User
  currentUserId: string
}

const props = defineProps<Props>()

defineEmits<{
  edit: [user: User]
  delete: [user: User]
  resetPassword: [user: User]
}>()

const isLastSuperuser = computed(() => false)
</script>
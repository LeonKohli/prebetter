<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button
        variant="ghost"
        size="icon"
        class="size-8 p-0 text-muted-foreground hover:text-foreground"
        aria-label="Open actions menu"
      >
        <Icon name="lucide:more-horizontal" class="size-4" />
        <span class="sr-only">Open menu</span>
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end">
      <DropdownMenuLabel>Actions</DropdownMenuLabel>
      <DropdownMenuSeparator />
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
        class="text-destructive focus:text-destructive focus:bg-destructive/10"
        @click="$emit('delete', user)"
        :disabled="user.id === currentUserId || props.isLastSuperuser"
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
  isLastSuperuser?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isLastSuperuser: false,
})

defineEmits<{
  edit: [user: User]
  delete: [user: User]
  resetPassword: [user: User]
}>()
</script>

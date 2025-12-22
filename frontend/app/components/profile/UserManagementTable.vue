<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h3 class="font-display text-lg font-semibold">User Management</h3>
      <ProfileCreateUserDialog @create-success="handleUserCreated" />
    </div>

    <div class="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Username</TableHead>
            <TableHead>Email</TableHead>
            <TableHead>Full Name</TableHead>
            <TableHead>Role</TableHead>
            <TableHead>Created</TableHead>
            <TableHead class="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <template v-if="pending">
            <TableRow>
              <TableCell colspan="6" class="text-center py-8">
                <div class="flex items-center justify-center gap-2">
                  <Icon name="lucide:loader-2" class="size-4 animate-spin" />
                  Loading users...
                </div>
              </TableCell>
            </TableRow>
          </template>
          <template v-else-if="error">
            <TableRow>
              <TableCell colspan="6" class="text-center py-8 text-destructive">
                Error loading users: {{ error.message }}
              </TableCell>
            </TableRow>
          </template>
          <template v-else-if="users.length === 0">
            <TableRow>
              <TableCell colspan="6" class="text-center py-8 text-muted-foreground">
                No users found
              </TableCell>
            </TableRow>
          </template>
          <template v-else>
            <TableRow v-for="user in users" :key="user.id">
              <TableCell class="font-medium">{{ user.username }}</TableCell>
              <TableCell>{{ user.email }}</TableCell>
              <TableCell>{{ user.full_name || '-' }}</TableCell>
              <TableCell>
                <Badge :variant="user.is_superuser ? 'default' : 'secondary'">
                  {{ user.is_superuser ? 'Admin' : 'User' }}
                </Badge>
              </TableCell>
              <TableCell>{{ formatDate(user.created_at) }}</TableCell>
              <TableCell class="text-right">
                <ProfileUserActions
                  :user="user"
                  :current-user-id="currentUserId"
                  :is-last-superuser="user.is_superuser && superuserCount === 1"
                  @edit="handleEditUser"
                  @delete="handleDeleteUser"
                  @reset-password="handleResetPassword"
                />
              </TableCell>
            </TableRow>
          </template>
        </TableBody>
      </Table>
    </div>

    <div v-if="totalPages > 1" class="flex items-center justify-between">
      <p class="text-sm text-muted-foreground">
        Showing {{ startItem }}-{{ endItem }} of {{ totalItems }} users
      </p>
      <div class="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          :disabled="currentPage === 1"
          @click="currentPage = currentPage - 1"
        >
          <Icon name="lucide:chevron-left" class="size-4" />
          Previous
        </Button>
        <span class="text-sm">Page {{ currentPage }} of {{ totalPages }}</span>
        <Button
          variant="outline"
          size="sm"
          :disabled="currentPage === totalPages"
          @click="currentPage = currentPage + 1"
        >
          Next
          <Icon name="lucide:chevron-right" class="size-4" />
        </Button>
      </div>
    </div>

    <ProfileEditUserDialog
      ref="editDialog"
      :user="selectedUser"
      @update:success="handleUserUpdated"
    />

    <AlertDialog v-model:open="isDeleteDialogOpen">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle class="flex items-center gap-2">
            <Icon name="lucide:trash-2" class="h-5 w-5 text-destructive" />
            Delete User
          </AlertDialogTitle>
          <AlertDialogDescription>
            This action cannot be undone. This will permanently delete the user account for <strong>{{ userToDelete?.username }}</strong>.
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div v-if="userToDelete" class="rounded-lg border bg-muted/50 p-4">
          <dl class="space-y-3 text-sm">
            <div class="flex items-start justify-between gap-4">
              <dt class="text-xs font-medium text-muted-foreground">Username</dt>
              <dd class="font-mono text-sm">{{ userToDelete.username }}</dd>
            </div>
            <div class="flex items-start justify-between gap-4">
              <dt class="text-xs font-medium text-muted-foreground">Email</dt>
              <dd class="text-sm">{{ userToDelete.email }}</dd>
            </div>
            <div v-if="userToDelete.is_superuser" class="flex items-start justify-between gap-4">
              <dt class="text-xs font-medium text-muted-foreground">Role</dt>
              <dd class="flex items-center gap-1.5 text-sm">
                <Icon name="lucide:shield-check" class="h-3.5 w-3.5 text-primary" />
                Superuser
              </dd>
            </div>
          </dl>
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel as-child>
            <Button variant="outline">
              Cancel
            </Button>
          </AlertDialogCancel>
          <AlertDialogAction as-child>
            <Button variant="destructive" @click="confirmDelete">
              Delete User
            </Button>
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    <ProfileResetPasswordDialog
      ref="resetPasswordDialog"
      :user="userToReset"
      @reset:success="handlePasswordReset"
    />
  </div>
</template>

<script setup lang="ts">
import type { User } from '#auth-utils'

// Type for dialog components that expose an open() method
interface DialogRef {
  open: () => void
}

interface UserWithTimestamps extends User {
  created_at: string
  updated_at?: string | null
}

interface Props {
  currentUserId: string
}

const props = defineProps<Props>()

const currentPage = ref(1)
const pageSize = ref(100)
const selectedUser = ref<UserWithTimestamps | null>(null)
const userToDelete = ref<UserWithTimestamps | null>(null)
const userToReset = ref<UserWithTimestamps | null>(null)
const isDeleteDialogOpen = ref(false)

const { data: response, pending, error, refresh } = await useFetch<{
  items: UserWithTimestamps[]
  pagination: {
    total: number
    page: number
    size: number
    pages: number
  }
}>('/api/users', {
  query: {
    page: currentPage,
    size: pageSize,
  },
  watch: [currentPage, pageSize],
})

const users = computed(() => response.value?.items || [])
const superuserCount = computed(() => users.value.filter(u => u.is_superuser).length)
const totalPages = computed(() => response.value?.pagination.pages || 1)
const totalItems = computed(() => response.value?.pagination.total || 0)
const startItem = computed(() => ((currentPage.value - 1) * pageSize.value) + 1)
const endItem = computed(() => Math.min(currentPage.value * pageSize.value, totalItems.value))

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

const handleUserCreated = (user: User) => {
  refresh()
}

const editDialog = ref<DialogRef | null>(null)
const resetPasswordDialog = ref<DialogRef | null>(null)

const handleEditUser = (user: UserWithTimestamps) => {
  selectedUser.value = user
  nextTick(() => {
    editDialog.value?.open()
  })
}

const handleUserUpdated = async (updatedUser: User) => {
  refresh()
  
  // Critical: Refresh session if user edited their own profile
  const session = useUserSession()
  if (session.user.value && session.user.value.id === updatedUser.id) {
    await session.fetch()
  }
  
}

const handleDeleteUser = (user: UserWithTimestamps) => {
  userToDelete.value = user
  isDeleteDialogOpen.value = true
}

const confirmDelete = async () => {
  if (!userToDelete.value) return
  
  try {
    await $fetch(`/api/users/${userToDelete.value.id}`, {
      method: 'DELETE',
    })
    refresh()
  } catch (error) {
    console.error('Delete user error:', error)
  } finally {
    isDeleteDialogOpen.value = false
    userToDelete.value = null
  }
}

const handleResetPassword = (user: UserWithTimestamps) => {
  userToReset.value = user
  nextTick(() => {
    resetPasswordDialog.value?.open()
  })
}

const handlePasswordReset = () => {
  userToReset.value = null
  refresh()
}
</script>
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
              <TableCell class="font-medium">{{ user.username || user.name }}</TableCell>
              <TableCell>{{ user.email }}</TableCell>
              <TableCell>{{ user.name || '-' }}</TableCell>
              <TableCell>
                <Badge :variant="user.role === 'admin' ? 'default' : 'secondary'">
                  {{ user.role === 'admin' ? 'Admin' : 'User' }}
                </Badge>
              </TableCell>
              <TableCell>{{ formatDate(user.createdAt) }}</TableCell>
              <TableCell class="text-right">
                <ProfileUserActions
                  :user="user"
                  :current-user-id="currentUserId"
                  :is-last-superuser="user.role === 'admin' && superuserCount === 1"
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
            <div v-if="userToDelete.role === 'admin'" class="flex items-start justify-between gap-4">
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
// Type for dialog components that expose an open() method
interface DialogRef {
  open: () => void
}

interface Props {
  currentUserId: string
}

const props = defineProps<Props>()

const { user: currentUser, refetch: refetchSession } = useAuth()

const currentPage = ref(1)
const pageSize = ref(100)
const selectedUser = ref<AppUser | null>(null)
const userToDelete = ref<AppUser | null>(null)
const userToReset = ref<AppUser | null>(null)
const isDeleteDialogOpen = ref(false)

// Admin endpoints are session-cookie authenticated and client-side only.
const { data: response, status, error, refresh } = await useAsyncData(
  'admin-users',
  async () => {
    const { data, error: listError } = await authClient.admin.listUsers({
      query: {
        limit: pageSize.value,
        offset: (currentPage.value - 1) * pageSize.value,
        sortBy: 'createdAt',
        sortDirection: 'desc',
      },
    })
    if (listError) throw new Error(listError.message || 'Failed to load users')
    return data
  },
  { watch: [currentPage, pageSize], server: false },
)

const pending = computed(() => status.value === 'pending')
const users = computed(() => (response.value?.users ?? []) as AppUser[])
const superuserCount = computed(() => users.value.filter(u => u.role === 'admin').length)
const totalItems = computed(() => response.value?.total ?? 0)
const totalPages = computed(() => Math.max(1, Math.ceil(totalItems.value / pageSize.value)))
const startItem = computed(() => ((currentPage.value - 1) * pageSize.value) + 1)
const endItem = computed(() => Math.min(currentPage.value * pageSize.value, totalItems.value))

const formatDate = (date: string | Date) => {
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

const handleUserCreated = () => {
  refresh()
}

const editDialog = ref<DialogRef | null>(null)
const resetPasswordDialog = ref<DialogRef | null>(null)

const handleEditUser = (user: AppUser) => {
  selectedUser.value = user
  nextTick(() => {
    editDialog.value?.open()
  })
}

const handleUserUpdated = async (updatedUser: AppUser) => {
  refresh()

  // Critical: Refresh session if the admin edited their own profile
  if (currentUser.value?.id === updatedUser.id) {
    await refetchSession()
  }
}

const handleDeleteUser = (user: AppUser) => {
  userToDelete.value = user
  isDeleteDialogOpen.value = true
}

const confirmDelete = async () => {
  if (!userToDelete.value) return

  try {
    const { error: removeError } = await authClient.admin.removeUser({
      userId: userToDelete.value.id,
    })
    if (removeError) throw new Error(removeError.message || 'Failed to delete user')
    refresh()
  } catch (error) {
    console.error('Delete user error:', error)
  } finally {
    isDeleteDialogOpen.value = false
    userToDelete.value = null
  }
}

const handleResetPassword = (user: AppUser) => {
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
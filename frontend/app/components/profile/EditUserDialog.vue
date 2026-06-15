<template>
  <Dialog v-model:open="isOpen">
    <DialogContent class="sm:max-w-[425px]">
      <DialogHeader>
        <DialogTitle>Edit User</DialogTitle>
        <DialogDescription>
          Update user information. Click save when you're done.
        </DialogDescription>
      </DialogHeader>

      <form @submit="onSubmit">
        <div class="grid gap-4 py-4">
          <FormField v-slot="{ componentField }" name="username">
            <FormItem>
              <FormLabel>Username</FormLabel>
              <FormControl>
                <Input v-bind="componentField" placeholder="Enter username" disabled />
              </FormControl>
              <FormDescription>Username cannot be changed</FormDescription>
              <FormMessage />
            </FormItem>
          </FormField>

          <FormField v-slot="{ componentField }" name="email">
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" v-bind="componentField" placeholder="Enter email" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>

          <FormField v-slot="{ componentField }" name="fullName">
            <FormItem>
              <FormLabel>Full Name</FormLabel>
              <FormControl>
                <Input v-bind="componentField" placeholder="Enter full name" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>

          <FormField v-slot="{ value, handleChange }" name="isSuperuser" type="checkbox" :unchecked-value="false">
            <FormItem class="flex flex-row items-start space-x-3 space-y-0">
              <FormControl>
                <Checkbox :checked="value" @update:checked="handleChange" />
              </FormControl>
              <div class="space-y-1 leading-none">
                <FormLabel>Administrator</FormLabel>
                <FormDescription>
                  Grant full admin privileges to this user
                </FormDescription>
              </div>
            </FormItem>
          </FormField>
        </div>

        <DialogFooter>
          <DialogClose as-child>
            <Button type="button" variant="outline" :disabled="isSubmitting">
              Cancel
            </Button>
          </DialogClose>
          <Button type="submit" :disabled="isSubmitting || !meta.dirty">
            <Icon v-if="isSubmitting" name="lucide:loader-2" class="mr-2 size-4 animate-spin" />
            {{ isSubmitting ? 'Saving...' : 'Save changes' }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { toFormValidator } from '@vee-validate/zod'
import { useForm } from 'vee-validate'

interface Props {
  user: AppUser | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  updateSuccess: [user: AppUser]
}>()

// Dialog state
const isOpen = ref(false)

// Form setup with useForm - the canonical vee-validate pattern
// Note: initialValues are computed to react to prop changes
const form = useForm({
  validationSchema: toFormValidator(userEditSchema),
  initialValues: {
    username: props.user?.username ?? '',
    email: props.user?.email ?? '',
    fullName: props.user?.name ?? '',
    isSuperuser: props.user?.role === 'admin',
  },
})

const { isSubmitting, setFieldError, meta, resetForm, setValues } = form

// Update form values when user prop changes
watch(() => props.user, (newUser) => {
  if (newUser) {
    const values = {
      username: newUser.username ?? '',
      email: newUser.email,
      fullName: newUser.name ?? '',
      isSuperuser: newUser.role === 'admin',
    }
    setValues(values)
    resetForm({ values }) // reset dirty state after applying prop values
  }
})

// handleSubmit returns a properly typed submit handler
const onSubmit = form.handleSubmit(async (values) => {
  if (!props.user) return

  const emailChanged = values.email !== props.user.email
  const nameChanged = values.fullName !== (props.user.name ?? '')
  const roleChanged = values.isSuperuser !== (props.user.role === 'admin')

  if (!emailChanged && !nameChanged && !roleChanged) {
    isOpen.value = false
    return
  }

  // Profile fields (email/name) go through update-user; role through set-role.
  if (emailChanged || nameChanged) {
    const data: Record<string, string> = {}
    if (emailChanged) data.email = values.email
    if (nameChanged) data.name = values.fullName || ''
    const { error } = await authClient.admin.updateUser({ userId: props.user.id, data })
    if (error) {
      setFieldError('email', error.message || 'Failed to update user')
      return
    }
  }

  if (roleChanged) {
    const { error } = await authClient.admin.setRole({
      userId: props.user.id,
      role: values.isSuperuser ? 'admin' : 'user',
    })
    if (error) {
      setFieldError('email', error.message || 'Failed to change role')
      return
    }
  }

  emit('updateSuccess', {
    ...props.user,
    email: values.email,
    name: values.fullName || '',
    role: values.isSuperuser ? 'admin' : 'user',
  })
  isOpen.value = false
})

// Expose open method for parent component
defineExpose({
  open: () => {
    isOpen.value = true
  }
})
</script>

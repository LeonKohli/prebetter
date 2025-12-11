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

          <FormField v-slot="{ componentField }" name="isSuperuser" type="checkbox" :unchecked-value="false">
            <FormItem class="flex flex-row items-start space-x-3 space-y-0">
              <FormControl>
                <Checkbox v-bind="componentField" />
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
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import type { User } from '#auth-utils'

interface Props {
  user: User | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  updateSuccess: [user: User]
}>()

// Dialog state
const isOpen = ref(false)

// Form setup with useForm - the canonical vee-validate pattern
// Note: initialValues are computed to react to prop changes
const form = useForm({
  validationSchema: toTypedSchema(userEditSchema),
  initialValues: {
    username: props.user?.username ?? '',
    email: props.user?.email ?? '',
    fullName: props.user?.full_name ?? '',
    isSuperuser: props.user?.is_superuser ?? false,
  },
})

const { isSubmitting, setFieldError, meta, resetForm, setValues } = form

// Update form values when user prop changes
watch(() => props.user, (newUser) => {
  if (newUser) {
    setValues({
      username: newUser.username,
      email: newUser.email,
      fullName: newUser.full_name ?? '',
      isSuperuser: newUser.is_superuser,
    })
    // Reset dirty state after setting values from prop
    resetForm({
      values: {
        username: newUser.username,
        email: newUser.email,
        fullName: newUser.full_name ?? '',
        isSuperuser: newUser.is_superuser,
      },
    })
  }
})

// handleSubmit returns a properly typed submit handler
const onSubmit = form.handleSubmit(async (values) => {
  if (!props.user) return

  try {
    // Build update payload - only include changed fields
    const updates: Record<string, string | boolean | null> = {}
    if (values.email !== props.user.email) updates.email = values.email
    if (values.fullName !== props.user.full_name) updates.full_name = values.fullName || null
    if (values.isSuperuser !== props.user.is_superuser) updates.is_superuser = values.isSuperuser

    // Skip if no changes
    if (Object.keys(updates).length === 0) {
      isOpen.value = false
      return
    }

    const data = await $fetch<User>(`/api/users/${props.user.id}`, {
      method: 'PUT',
      body: updates,
    })

    // Emit success event
    emit('updateSuccess', data)
    isOpen.value = false
  } catch (error) {
    console.error('Update user error:', error)

    // Handle specific errors
    const fetchError = error as { data?: { detail?: string } }
    if (fetchError.data?.detail) {
      const detail = fetchError.data.detail
      if (detail.includes('Email already')) {
        setFieldError('email', 'Email is already in use')
      } else {
        setFieldError('email', detail)
      }
    }
  }
})

// Expose open method for parent component
defineExpose({
  open: () => {
    isOpen.value = true
  }
})
</script>

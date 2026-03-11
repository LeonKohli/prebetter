<template>
  <Dialog v-model:open="isOpen">
    <DialogTrigger as-child>
      <Button variant="outline" size="sm">
        <Icon name="lucide:key" class="mr-2 size-4" />
        Change Password
      </Button>
    </DialogTrigger>
    <DialogContent class="sm:max-w-[425px]">
      <DialogHeader>
        <DialogTitle>Change Password</DialogTitle>
        <DialogDescription>
          Enter your current password and choose a new one.
        </DialogDescription>
      </DialogHeader>

      <form @submit="onSubmit">
        <div class="grid gap-4 py-4">
          <FormField v-slot="{ field }" name="currentPassword">
            <FormItem>
              <FormLabel>Current Password</FormLabel>
              <FormControl>
                <Input type="password" v-bind="field" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>

          <FormField v-slot="{ field }" name="newPassword">
            <FormItem>
              <FormLabel>New Password</FormLabel>
              <FormControl>
                <Input type="password" v-bind="field" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>

          <FormField v-slot="{ field }" name="confirmPassword">
            <FormItem>
              <FormLabel>Confirm New Password</FormLabel>
              <FormControl>
                <Input type="password" v-bind="field" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>
        </div>

        <DialogFooter>
          <DialogClose as-child>
            <Button type="button" variant="outline" :disabled="isSubmitting">
              Cancel
            </Button>
          </DialogClose>
          <Button type="submit" :disabled="isSubmitting">
            <Icon v-if="isSubmitting" name="lucide:loader-2" class="mr-2 size-4 animate-spin" />
            {{ isSubmitting ? 'Changing...' : 'Change Password' }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { toFormValidator } from '@vee-validate/zod'
import { useForm } from 'vee-validate'

// Emits
const emit = defineEmits<{
  updateSuccess: []
}>()

// State
const isOpen = ref(false)

// Form setup with useForm - the canonical vee-validate pattern
const form = useForm({
  validationSchema: toFormValidator(changePasswordSchema),
  initialValues: {
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  },
})

const { isSubmitting, setFieldError } = form

// handleSubmit returns a properly typed submit handler
const onSubmit = form.handleSubmit(async (values) => {
  try {
    await $fetch('/api/users/change-password', {
      method: 'POST',
      body: {
        current_password: values.currentPassword,
        new_password: values.newPassword,
      },
    })

    // Emit success event
    emit('updateSuccess')

    // Close dialog
    isOpen.value = false
  } catch (error) {
    console.error('Password change error:', error)

    const fetchError = error as { data?: { detail?: string | Array<{ loc: string[]; msg: string }> } }
    const detail = fetchError.data?.detail
    if (!detail) return

    if (typeof detail === 'string') {
      if (detail.includes('Incorrect current password')) {
        setFieldError('currentPassword', 'Current password is incorrect')
      } else {
        setFieldError('currentPassword', detail)
      }
      return
    }

    const fieldMap: Record<string, string> = { current_password: 'currentPassword', new_password: 'newPassword' }
    for (const err of detail) {
      const backendField = err.loc[err.loc.length - 1]
      setFieldError(fieldMap[backendField] || backendField, err.msg)
    }
  }
})
</script>

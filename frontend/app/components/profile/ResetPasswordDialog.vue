<template>
  <Dialog v-model:open="isOpen">
    <DialogContent class="sm:max-w-[425px]">
      <DialogHeader>
        <DialogTitle>Reset Password</DialogTitle>
        <DialogDescription>
          Set a new password for <strong>{{ user?.username }}</strong>. They will be required to change it on next login.
        </DialogDescription>
      </DialogHeader>

      <form @submit="onSubmit">
        <div class="grid gap-4 py-4">
          <FormField v-slot="{ componentField }" name="newPassword">
            <FormItem>
              <FormLabel>New Password</FormLabel>
              <FormControl>
                <div class="flex gap-2">
                  <Input type="text" v-bind="componentField" placeholder="Enter new password" />
                  <Button type="button" size="sm" variant="outline" @click="generatePassword">
                    <Icon name="lucide:dice-3" class="size-4" />
                  </Button>
                </div>
              </FormControl>
              <FormDescription>
                The user will be prompted to change this password on their next login
              </FormDescription>
              <FormMessage />
            </FormItem>
          </FormField>

          <Alert>
            <Icon name="lucide:info" class="size-4" />
            <AlertTitle>Note</AlertTitle>
            <AlertDescription>
              Make sure to securely communicate the new password to the user.
            </AlertDescription>
          </Alert>
        </div>

        <DialogFooter>
          <DialogClose as-child>
            <Button type="button" variant="outline" :disabled="isSubmitting">
              Cancel
            </Button>
          </DialogClose>
          <Button type="submit" :disabled="isSubmitting">
            <Icon v-if="isSubmitting" name="lucide:loader-2" class="mr-2 size-4 animate-spin" />
            {{ isSubmitting ? 'Resetting...' : 'Reset Password' }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'

interface User {
  id: string
  username: string
  email: string
  created_at: string
  updated_at?: string | null
}

interface Props {
  user: User | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'reset:success': []
}>()

// Dialog state
const isOpen = ref(false)

// Form setup with useForm - the canonical vee-validate pattern
const form = useForm({
  validationSchema: toTypedSchema(resetPasswordSchema),
  initialValues: {
    newPassword: '',
  },
})

const { isSubmitting, setFieldValue, resetForm } = form

// Generate random password
const generatePassword = () => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*'
  let password = ''
  for (let i = 0; i < 12; i++) {
    password += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  setFieldValue('newPassword', password)
}

// handleSubmit returns a properly typed submit handler
const onSubmit = form.handleSubmit(async (values) => {
  if (!props.user) return

  try {
    await $fetch(`/api/users/${props.user.id}/reset-password`, {
      method: 'POST',
      body: {
        new_password: values.newPassword,
      },
    })

    // Emit success event
    emit('reset:success')
    isOpen.value = false
    resetForm()
  } catch (error) {
    console.error('Reset password error:', error)
  }
})

// Expose open method for parent component
defineExpose({
  open: () => {
    isOpen.value = true
  }
})
</script>

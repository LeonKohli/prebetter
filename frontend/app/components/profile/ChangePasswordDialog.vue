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
      
      <Form v-slot="{ setFieldError }" :validation-schema="formSchema" :initial-values="initialValues" @submit="onSubmit">
        <div class="grid gap-4 py-4">
          <FormField v-slot="{ componentField }" name="currentPassword">
            <FormItem>
              <FormLabel>Current Password</FormLabel>
              <FormControl>
                <Input type="password" v-bind="componentField" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>

          <FormField v-slot="{ componentField }" name="newPassword">
            <FormItem>
              <FormLabel>New Password</FormLabel>
              <FormControl>
                <Input type="password" v-bind="componentField" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>

          <FormField v-slot="{ componentField }" name="confirmPassword">
            <FormItem>
              <FormLabel>Confirm New Password</FormLabel>
              <FormControl>
                <Input type="password" v-bind="componentField" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>
        </div>
        
        <DialogFooter>
          <Button type="button" variant="outline" @click="handleCancel" :disabled="isSubmitting">
            Cancel
          </Button>
          <Button type="submit" :disabled="isSubmitting">
            <Icon v-if="isSubmitting" name="lucide:loader-2" class="mr-2 size-4 animate-spin" />
            {{ isSubmitting ? 'Changing...' : 'Change Password' }}
          </Button>
        </DialogFooter>
      </Form>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { toTypedSchema } from '@vee-validate/zod'
import { Form } from '@/components/ui/form'

// Emits
const emit = defineEmits<{
  'update:success': []
}>()

// State
const isOpen = ref(false)
const isSubmitting = ref(false)

// Form validation
const formSchema = toTypedSchema(changePasswordSchema)

// Initial form values
const initialValues = {
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
}



// Handle cancel
const handleCancel = () => {
  isOpen.value = false
}

// Form submission
const onSubmit = async (values: any, { setFieldError }: any) => {
  isSubmitting.value = true
  
  try {
    await $fetch('/api/users/change-password', {
      method: 'POST',
      body: {
        current_password: values.currentPassword,
        new_password: values.newPassword,
      },
    })

    // Emit success event
    emit('update:success')
    
    // Close dialog
    isOpen.value = false
  } catch (error) {
    console.error('Password change error:', error)
    
    // Handle specific errors
    const fetchError = error as { data?: { detail?: string } }
    if (fetchError.data?.detail) {
      const detail = fetchError.data.detail
      if (detail.includes('Incorrect current password')) {
        setFieldError('currentPassword', 'Current password is incorrect')
      } else {
        setFieldError('currentPassword', detail)
      }
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>


<template>
  <Dialog v-model:open="isOpen">
    <DialogTrigger as-child>
      <Button variant="outline" size="sm">
        <Icon name="lucide:edit" class="mr-2 size-4" />
        Edit Profile
      </Button>
    </DialogTrigger>
    <DialogContent class="sm:max-w-[425px]">
      <DialogHeader>
        <DialogTitle>Edit Profile</DialogTitle>
        <DialogDescription>
          Update your profile information below. Your current information is already filled in. Click save when you're done.
        </DialogDescription>
      </DialogHeader>
      
      <Form v-slot="{ meta }" :validation-schema="formSchema" :initial-values="initialValues" @submit="onSubmit">
        <div class="grid gap-4 py-4">
          <FormField v-slot="{ componentField }" name="username">
            <FormItem>
              <FormLabel>Username</FormLabel>
              <FormControl>
                <Input v-bind="componentField" placeholder="Enter username" />
              </FormControl>
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
              <FormLabel>Full Name <span class="text-muted-foreground text-sm">(optional)</span></FormLabel>
              <FormControl>
                <Input v-bind="componentField" placeholder="Enter your full name" />
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
          <Button type="submit" :disabled="isSubmitting || !meta.dirty">
            <Icon v-if="isSubmitting" name="lucide:loader-2" class="mr-2 size-4 animate-spin" />
            {{ isSubmitting ? 'Saving...' : 'Save changes' }}
          </Button>
        </DialogFooter>
      </Form>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { toTypedSchema } from '@vee-validate/zod'
import type { User } from '#auth-utils'
import { Form } from '@/components/ui/form'

interface Props {
  user: User
}

const props = defineProps<Props>()
const emit = defineEmits<{
  updateSuccess: []
}>()

// Dialog state
const isOpen = ref(false)
const isSubmitting = ref(false)

const formSchema = toTypedSchema(profileEditSchema)

// Initial values
const initialValues = computed(() => ({
  username: props.user.username,
  email: props.user.email,
  fullName: props.user.full_name || '',
}))

const onSubmit = async (values: any, { setFieldError }: any) => {
  isSubmitting.value = true
  
  try {
    // Clean up values - only send changed fields
    const updates: Record<string, string | null> = {}
    if (values.username !== props.user.username) updates.username = values.username
    if (values.email !== props.user.email) updates.email = values.email
    if (values.fullName !== props.user.full_name) updates.full_name = values.fullName || null

    // Skip if no changes
    if (Object.keys(updates).length === 0) {
      isOpen.value = false
      return
    }

    // Update profile via API
    await $fetch('/api/auth/users/me', {
      method: 'PUT',
      body: updates,
    })

    // Emit success event (parent will handle session refresh)
    emit('updateSuccess')
    
    // Close dialog
    isOpen.value = false
  } catch (error) {
    console.error('Profile update error:', error)
    
    // Handle specific errors
    const fetchError = error as { data?: { detail?: string } }
    if (fetchError.data?.detail) {
      const detail = fetchError.data.detail
      if (detail.includes('Username already')) {
        setFieldError('username', 'Username is already taken')
      } else if (detail.includes('Email already')) {
        setFieldError('email', 'Email is already in use')
      } else {
        // Show generic error
        setFieldError('username', detail)
      }
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

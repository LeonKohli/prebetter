<template>
  <Dialog v-model:open="isOpen">
    <DialogTrigger as-child>
      <Button size="sm">
        <Icon name="lucide:plus" class="mr-2 size-4" />
        Add User
      </Button>
    </DialogTrigger>
    <DialogContent class="sm:max-w-[425px]">
      <DialogHeader>
        <DialogTitle>Create New User</DialogTitle>
        <DialogDescription>
          Create a new user account with the specified credentials.
        </DialogDescription>
      </DialogHeader>
      
      <Form v-slot="{ resetForm }" :validation-schema="formSchema" :initial-values="initialValues" @submit="onSubmit">
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
              <FormLabel>Full Name</FormLabel>
              <FormControl>
                <Input v-bind="componentField" placeholder="Enter full name (optional)" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>

          <FormField v-slot="{ componentField }" name="password">
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <Input type="text" v-bind="componentField" placeholder="Enter password" />
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
          <Button type="button" variant="outline" @click="handleCancel(resetForm)" :disabled="isSubmitting">
            Cancel
          </Button>
          <Button type="submit" :disabled="isSubmitting">
            <Icon v-if="isSubmitting" name="lucide:loader-2" class="mr-2 size-4 animate-spin" />
            {{ isSubmitting ? 'Creating...' : 'Create User' }}
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

const emit = defineEmits<{
  'create:success': [user: User]
}>()

// Dialog state
const isOpen = ref(false)
const isSubmitting = ref(false)

// Form schema
const formSchema = toTypedSchema(userCreateSchema)

// Initial form values
const initialValues = {
  username: '',
  email: '',
  fullName: '',
  password: '',
  isSuperuser: false,
}

// Watch for dialog open to reset form
watch(isOpen, (newValue) => {
  if (newValue) {
    // Form will reset automatically with initial values
  }
})

// Handle cancel
const handleCancel = (resetForm: any) => {
  resetForm()
  isOpen.value = false
}

// Form submission
const onSubmit = async (values: any, { resetForm, setFieldError }: any) => {
  isSubmitting.value = true
  
  try {
    const data = await $fetch('/api/users', {
      method: 'POST',
      body: {
        username: values.username,
        email: values.email,
        full_name: values.fullName || null,
        password: values.password,
        is_superuser: values.isSuperuser,
      },
    })

    // Emit success event
    emit('create:success', data as User)
    
    // Reset form and close dialog
    resetForm()
    isOpen.value = false
  } catch (error) {
    console.error('Create user error:', error)
    
    // Handle specific errors
    const fetchError = error as { data?: { detail?: string } }
    if (fetchError.data?.detail) {
      const detail = fetchError.data.detail
      if (detail.includes('Username already')) {
        setFieldError('username', 'Username is already taken')
      } else if (detail.includes('Email already')) {
        setFieldError('email', 'Email is already in use')
      } else {
        setFieldError('username', detail)
      }
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>
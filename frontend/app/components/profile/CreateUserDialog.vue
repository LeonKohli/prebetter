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

      <form @submit="onSubmit">
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
                <PasswordInput v-bind="componentField" placeholder="Enter password" />
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
            <Button type="button" variant="outline" @click="handleCancel" :disabled="isSubmitting">
              Cancel
            </Button>
          </DialogClose>
          <Button type="submit" :disabled="isSubmitting">
            <Icon v-if="isSubmitting" name="lucide:loader-2" class="mr-2 size-4 animate-spin" />
            {{ isSubmitting ? 'Creating...' : 'Create User' }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { toFormValidator } from '@vee-validate/zod'
import { useForm } from 'vee-validate'

const emit = defineEmits<{
  createSuccess: [user: AppUser]
}>()

// Dialog state
const isOpen = ref(false)

// Form setup with useForm - the canonical vee-validate pattern
const form = useForm({
  validationSchema: toFormValidator(userCreateSchema),
  initialValues: {
    username: '',
    email: '',
    fullName: '',
    password: '',
    isSuperuser: false,
  },
})

const { isSubmitting, setFieldError, resetForm } = form

const handleCancel = () => {
  resetForm()
}

// handleSubmit returns a properly typed submit handler
const onSubmit = form.handleSubmit(async (values) => {
  const name = values.fullName || values.username
  const { data, error } = await authClient.admin.createUser({
    email: values.email,
    password: values.password,
    name,
    role: values.isSuperuser ? 'admin' : 'user',
    // username/displayUsername are user-table fields added by the username plugin
    data: { username: values.username, displayUsername: values.username },
  })

  if (error) {
    if (error.code === 'USERNAME_IS_ALREADY_TAKEN') {
      setFieldError('username', 'Username is already taken')
    } else if (error.code?.includes('USER_ALREADY_EXISTS')) {
      setFieldError('email', 'Email is already in use')
    } else {
      setFieldError('username', error.message || 'Failed to create user')
    }
    return
  }

  emit('createSuccess', data.user as AppUser)
  resetForm()
  isOpen.value = false
})
</script>

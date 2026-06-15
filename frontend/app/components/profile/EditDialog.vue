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
      </form>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { toFormValidator } from '@vee-validate/zod'
import { useForm } from 'vee-validate'

interface Props {
  user: { id: string; username?: string | null; name?: string | null; email: string }
}

const props = defineProps<Props>()
const emit = defineEmits<{
  updateSuccess: []
}>()

// Dialog state
const isOpen = ref(false)

const form = useForm({
  validationSchema: toFormValidator(selfProfileEditSchema),
  initialValues: {
    username: props.user.username ?? '',
    fullName: props.user.name ?? '',
  },
})

const { isSubmitting, setFieldError, meta, resetForm, setValues } = form

// Update form values when user prop changes
watch(() => props.user, (newUser) => {
  const values = {
    username: newUser.username ?? '',
    fullName: newUser.name ?? '',
  }
  setValues(values)
  resetForm({ values })
}, { deep: true })

// handleSubmit returns a properly typed submit handler
const onSubmit = form.handleSubmit(async (values) => {
  const usernameChanged = values.username !== (props.user.username ?? '')
  const nameChanged = values.fullName !== (props.user.name ?? '')

  if (!usernameChanged && !nameChanged) {
    isOpen.value = false
    return
  }

  const { error } = await authClient.updateUser({
    name: values.fullName || undefined,
    username: usernameChanged ? values.username : undefined,
  })

  if (!error) {
    emit('updateSuccess')
    isOpen.value = false
    return
  }

  if (error.code === 'USERNAME_IS_ALREADY_TAKEN') {
    setFieldError('username', 'Username is already taken')
  } else {
    setFieldError('username', error.message || 'Failed to update profile')
  }
})
</script>

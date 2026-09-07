import { auth } from '../server/utils/auth'

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error(`Missing required env var: ${name}`)
  return value
}

await auth.api.createUser({
  body: {
    name: required('ADMIN_USERNAME'),
    email: required('ADMIN_EMAIL'),
    password: required('ADMIN_PASSWORD'),
    role: 'admin',
    data: { username: required('ADMIN_USERNAME') },
  },
})
console.log('Administrator created')
process.exit(0)

import { z } from 'zod'

// Strict schemas for create/edit forms
// Zod 4: Use { error: 'message' } instead of string shorthand
export const usernameSchema = z
  .string()
  .min(3, { error: 'Username must be at least 3 characters' })
  .max(50, { error: 'Username must be less than 50 characters' })

export const emailSchema = z
  .string()
  .email({ error: 'Invalid email address' })

export const fullNameSchema = z
  .string()
  .max(100, { error: 'Full name must be less than 100 characters' })
  .optional()
  .or(z.literal(''))

// Password schema - no frontend length enforcement, backend handles validation
export const passwordSchema = z.string()

export const profileEditSchema = z.object({
  username: usernameSchema,
  email: emailSchema,
  fullName: fullNameSchema,
})

export const userEditSchema = profileEditSchema.extend({
  isSuperuser: z.boolean(),
})

export const userCreateSchema = userEditSchema.extend({
  password: passwordSchema,
})

export const changePasswordSchema = z.object({
  currentPassword: passwordSchema,
  newPassword: passwordSchema,
  confirmPassword: passwordSchema,
}).refine((data) => data.newPassword === data.confirmPassword, {
  error: "Passwords don't match",
  path: ['confirmPassword'],
})

export const resetPasswordSchema = z.object({
  newPassword: passwordSchema,
})

// Login schema - minimal validation, backend handles actual auth
export const loginSchema = z.object({
  username: z.string(),
  password: z.string(),
})

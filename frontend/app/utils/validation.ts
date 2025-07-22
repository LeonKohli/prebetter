/**
 * Shared validation schemas and rules
 */
import { z } from 'zod'

// Common field schemas
export const usernameSchema = z
  .string()
  .min(3, 'Username must be at least 3 characters')
  .max(50, 'Username must be less than 50 characters')

export const emailSchema = z
  .string()
  .email('Invalid email address')

export const passwordSchema = z
  .string()
  .min(1, 'Password is required')

export const fullNameSchema = z
  .string()
  .max(100, 'Full name must be less than 100 characters')
  .optional()
  .or(z.literal(''))

// User profile schemas
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
  currentPassword: z.string().min(1, 'Current password is required'),
  newPassword: passwordSchema,
  confirmPassword: z.string().min(1, 'Please confirm your password'),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
})

export const resetPasswordSchema = z.object({
  newPassword: z.string().min(8, 'Password must be at least 8 characters'),
})
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { Updater } from '@tanstack/vue-table'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function valueUpdater<T extends unknown>(
  updaterOrValue: Updater<T> | T, 
  ref: Ref<T>
): void {
  if (typeof updaterOrValue === 'function') {
    ref.value = (updaterOrValue as (old: T) => T)(ref.value)
  } else {
    ref.value = updaterOrValue
  }
}

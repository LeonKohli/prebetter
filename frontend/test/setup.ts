// Test setup file for Vitest
import { vi } from 'vitest'

// Mock process.env for SSR-like behavior
if (!global.process) {
  global.process = {} as any
}
if (!global.process.env) {
  global.process.env = {}
}
global.process.client = false
global.process.server = true
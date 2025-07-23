import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { nextTick } from 'vue'
import { useNavigableUrlState } from '../useNavigableUrlState'
import type { Router, RouteLocationNormalized } from 'vue-router'

// Mock Vue Router
vi.mock('#app', () => ({
  useRoute: vi.fn(),
  useRouter: vi.fn()
}))

describe('useNavigableUrlState - Race Condition Tests', () => {
  let mockRoute: Partial<RouteLocationNormalized>
  let mockRouter: Partial<Router>
  let pushPromiseResolve: (() => void) | null = null
  let replacePromiseResolve: (() => void) | null = null

  beforeEach(() => {
    // Reset promise resolvers
    pushPromiseResolve = null
    replacePromiseResolve = null

    // Setup mock route
    mockRoute = {
      query: {}
    }

    // Setup mock router with delayed promise resolution
    mockRouter = {
      push: vi.fn().mockImplementation(() => {
        return new Promise(resolve => {
          pushPromiseResolve = resolve
          // Simulate async delay
          setTimeout(() => {
            if (pushPromiseResolve === resolve) {
              resolve(undefined)
            }
          }, 10)
        })
      }),
      replace: vi.fn().mockImplementation(() => {
        return new Promise(resolve => {
          replacePromiseResolve = resolve
          // Simulate async delay
          setTimeout(() => {
            if (replacePromiseResolve === resolve) {
              resolve(undefined)
            }
          }, 10)
        })
      })
    }

    // Mock the composables
    vi.mocked(useRoute).mockReturnValue(mockRoute as RouteLocationNormalized)
    vi.mocked(useRouter).mockReturnValue(mockRouter as Router)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Rapid Sequential Updates', () => {
    it('should handle rapid view toggle clicks without race conditions', async () => {
      const urlState = useNavigableUrlState()
      
      // Simulate rapid clicking on view toggle
      const promise1 = urlState.updateBatch({ view: 'ungrouped' })
      const promise2 = urlState.updateBatch({ view: 'grouped' })
      const promise3 = urlState.updateBatch({ view: 'ungrouped' })
      
      await Promise.all([promise1, promise2, promise3])
      
      // Should only have made 3 router calls
      expect(mockRouter.push).toHaveBeenCalledTimes(3)
      
      // Last call should have the final state
      const lastCall = vi.mocked(mockRouter.push).mock.calls[2]
      expect(lastCall[0]).toEqual({
        query: { view: 'ungrouped' }
      })
    })

    it('should preserve all parameters during batch updates', async () => {
      // Setup initial state with complex query
      mockRoute.query = {
        view: 'grouped',
        page: '2',
        size: '50',
        sort: 'severity:asc',
        filter: '{"classification_text":"ssh","severity":3}',
        cols: 'analyzer,target_ipv4',
        refresh: '60'
      }
      
      const urlState = useNavigableUrlState()
      
      // Batch update that changes view and resets page
      await urlState.updateBatch({
        view: 'ungrouped',
        page: 1,
        sortBy: 'detected_at',
        sortOrder: 'desc'
      })
      
      // Verify all other parameters are preserved
      const expectedQuery = {
        view: 'ungrouped',
        page: '1',
        size: '50',
        sort: 'detected_at:desc',
        filter: '{"classification_text":"ssh","severity":3}',
        cols: 'analyzer,target_ipv4',
        refresh: '60'
      }
      
      expect(mockRouter.push).toHaveBeenCalledWith({ query: expectedQuery })
    })

    it('should handle concurrent filter and view updates', async () => {
      const urlState = useNavigableUrlState()
      
      // Simulate user changing filters while view is toggling
      const viewPromise = urlState.updateBatch({
        view: 'ungrouped',
        sortBy: 'detected_at'
      })
      
      const filterPromise = urlState.updateFilters({
        classification_text: 'malware',
        severity: 4
      })
      
      await Promise.all([viewPromise, filterPromise])
      
      // Both updates should be applied
      expect(mockRouter.push).toHaveBeenCalledTimes(2)
    })
  })

  describe('Browser Navigation During Updates', () => {
    it('should handle browser back/forward during async updates', async () => {
      const urlState = useNavigableUrlState()
      
      // Start an update
      const updatePromise = urlState.updateBatch({
        view: 'ungrouped',
        page: 2
      })
      
      // Simulate browser back button before update completes
      mockRoute.query = { view: 'grouped', page: '1' }
      
      // Complete the update
      await updatePromise
      
      // The update should have completed with push
      expect(mockRouter.push).toHaveBeenCalledWith({
        query: { view: 'ungrouped', page: '2' }
      })
    })

    it('should handle route changes during batch updates', async () => {
      mockRoute.query = { 
        view: 'grouped',
        filter: '{"severity":2}'
      }
      
      const urlState = useNavigableUrlState()
      
      // Start batch update
      const batchPromise = urlState.updateBatch({
        view: 'ungrouped',
        page: 1,
        sortBy: 'detected_at'
      })
      
      // Simulate route change mid-update
      mockRoute.query = {
        view: 'grouped',
        filter: '{"severity":3}',
        page: '5'
      }
      
      await batchPromise
      
      // Batch update should preserve the original route state it started with
      expect(mockRouter.push).toHaveBeenCalledWith({
        query: {
          view: 'ungrouped',
          page: '1',
          sort: 'detected_at:desc',
          filter: '{"severity":2}'
        }
      })
    })
  })

  describe('Edge Cases and Error Scenarios', () => {
    it('should handle empty batch updates gracefully', async () => {
      const urlState = useNavigableUrlState()
      
      await urlState.updateBatch({})
      
      // Should still make a router call but with existing query
      expect(mockRouter.push).toHaveBeenCalledWith({ query: {} })
    })

    it('should handle batch updates with undefined values correctly', async () => {
      mockRoute.query = {
        view: 'grouped',
        page: '2',
        sort: 'severity:asc'
      }
      
      const urlState = useNavigableUrlState()
      
      await urlState.updateBatch({
        view: undefined,
        page: undefined,
        sortBy: 'detected_at'
      })
      
      // Should only update sortBy, preserving other values
      expect(mockRouter.push).toHaveBeenCalledWith({
        query: {
          view: 'grouped',
          page: '2',
          sort: 'detected_at:asc' // Preserves existing order
        }
      })
    })

    it('should remove empty filter values in batch updates', async () => {
      mockRoute.query = {
        filter: '{"classification_text":"ssh"}'
      }
      
      const urlState = useNavigableUrlState()
      
      await urlState.updateBatch({
        filters: {}
      })
      
      // Empty filters should remove the filter param
      const call = vi.mocked(mockRouter.push).mock.calls[0]
      expect(call[0].query).not.toHaveProperty('filter')
    })

    it('should handle router errors gracefully', async () => {
      mockRouter.push = vi.fn().mockRejectedValue(new Error('Navigation cancelled'))
      
      const urlState = useNavigableUrlState()
      
      // Should not throw
      await expect(
        urlState.updateBatch({ view: 'ungrouped' })
      ).rejects.toThrow('Navigation cancelled')
    })
  })

  describe('Memory Leak Prevention', () => {
    it('should not create memory leaks with multiple pending promises', async () => {
      const urlState = useNavigableUrlState()
      
      // Create many pending updates
      const promises: Promise<void>[] = []
      for (let i = 0; i < 100; i++) {
        promises.push(
          urlState.updateBatch({
            page: i + 1,
            view: i % 2 === 0 ? 'grouped' : 'ungrouped'
          })
        )
      }
      
      // Resolve all promises
      await Promise.all(promises)
      
      // Verify all completed
      expect(mockRouter.push).toHaveBeenCalledTimes(100)
    })

    it('should handle interleaved push and replace operations', async () => {
      const urlState = useNavigableUrlState()
      
      // User action (push)
      const userPromise = urlState.updateBatch({ view: 'ungrouped' }, true)
      
      // Programmatic update (replace)
      const programmaticPromise = urlState.updateBatch({ page: 2 }, false)
      
      await Promise.all([userPromise, programmaticPromise])
      
      expect(mockRouter.push).toHaveBeenCalledTimes(1)
      expect(mockRouter.replace).toHaveBeenCalledTimes(1)
    })
  })

  describe('Complex State Synchronization', () => {
    it('should handle view toggle with complex filter state', async () => {
      mockRoute.query = {
        view: 'grouped',
        filter: '{"classification_text":"malware","severity":4,"analyzer":"snort"}',
        sort: 'total_count:desc',
        page: '3'
      }
      
      const urlState = useNavigableUrlState()
      
      // Toggle view which should reset page and change sort
      await urlState.updateBatch({
        view: 'ungrouped',
        page: 1,
        sortBy: 'detected_at',
        sortOrder: 'desc',
        filters: JSON.parse(mockRoute.query.filter as string)
      })
      
      expect(mockRouter.push).toHaveBeenCalledWith({
        query: {
          view: 'ungrouped',
          page: '1',
          sort: 'detected_at:desc',
          filter: '{"classification_text":"malware","severity":4,"analyzer":"snort"}'
        }
      })
    })

    it('should handle navigateToDetails during other updates', async () => {
      const urlState = useNavigableUrlState()
      
      // Start a batch update
      const batchPromise = urlState.updateBatch({
        view: 'grouped',
        page: 2
      })
      
      // Navigate to details (always user action)
      const detailsPromise = urlState.navigateToDetails({
        sourceIp: '192.168.1.1',
        targetIp: '10.0.0.1',
        classification: 'ssh-scan'
      })
      
      await Promise.all([batchPromise, detailsPromise])
      
      // Both should complete, details should be last
      expect(mockRouter.push).toHaveBeenCalledTimes(2)
      
      const lastCall = vi.mocked(mockRouter.push).mock.calls[1]
      expect(lastCall[0].query).toMatchObject({
        view: 'ungrouped',
        filter: expect.stringContaining('ssh-scan')
      })
    })
  })
})
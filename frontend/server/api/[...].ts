import { joinURL } from 'ufo'
import type { H3Event } from 'h3'
import type { FetchError } from 'ofetch'

interface SessionData {
  secure?: {
    apiToken?: string
  }
}

export default defineEventHandler(async (event: H3Event) => {
  // Get the path from the event, which preserves trailing slashes
  const path = event.path.replace(/^\/api\//, '') // /api/users/ -> users/
  
  // Construct the full target URL
  const proxyUrl = useRuntimeConfig().apiBase as string
  const target = joinURL(proxyUrl, 'api/v1', path)
  
  // Get the current user session
  const session = await getUserSession(event) as SessionData
  
  // Get the secure API token from the session
  const apiToken = session.secure?.apiToken
  
  // Define headers, adding the Authorization header if the token exists
  const headers: Record<string, string> = {
    // Forward the 'accept' header from the original request
    'accept': getRequestHeader(event, 'accept') || 'application/json',
  }
  
  if (apiToken) {
    headers['Authorization'] = `Bearer ${apiToken}`
  }

  try {
    // Build fetch options with proper types
    const fetchOptions: Record<string, unknown> = {
      method: event.method,
      headers,
    }

    // Add body for non-GET/HEAD requests
    if (event.method !== 'GET' && event.method !== 'HEAD') {
      const body = await readBody(event)
      if (body !== undefined) {
        fetchOptions.body = body
      }
    }

    // Proxy the request to your backend using $fetch
    const response = await $fetch.raw(target, fetchOptions)
    
    // Return the response data
    return response._data
  } catch (error) {
    const fetchError = error as FetchError
    
    // If it's a fetch error with a response, forward the error properly
    if (fetchError.statusCode) {
      throw createError({
        statusCode: fetchError.statusCode,
        statusMessage: fetchError.statusMessage,
        data: fetchError.data,
      })
    }
    
    // Otherwise throw a generic error
    throw createError({
      statusCode: 502,
      statusMessage: 'Bad Gateway',
    })
  }
})
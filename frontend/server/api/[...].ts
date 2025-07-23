import { joinURL } from 'ufo'
import type { H3Event } from 'h3'
import type { FetchError } from 'ofetch'

interface SessionData {
  secure?: {
    apiToken?: string
  }
}

export default defineEventHandler(async (event: H3Event) => {
  // Preserve trailing slashes: /api/users/ -> users/
  const path = event.path.replace(/^\/api\//, '')
  
  const proxyUrl = useRuntimeConfig().apiBase as string
  const target = joinURL(proxyUrl, 'api/v1', path)
  
  const session = await getUserSession(event) as SessionData
  
  const apiToken = session.secure?.apiToken
  
  const headers: Record<string, string> = {
    'accept': getRequestHeader(event, 'accept') || 'application/json',
  }
  
  if (apiToken) {
    headers['Authorization'] = `Bearer ${apiToken}`
  }

  try {
    const fetchOptions: Record<string, unknown> = {
      method: event.method,
      headers,
    }

    if (event.method !== 'GET' && event.method !== 'HEAD') {
      const body = await readBody(event)
      if (body !== undefined) {
        fetchOptions.body = body
      }
    }

    const response = await $fetch.raw(target, fetchOptions)
    return response._data
  } catch (error) {
    const fetchError = error as FetchError
    
    if (fetchError.statusCode) {
      throw createError({
        statusCode: fetchError.statusCode,
        statusMessage: fetchError.statusMessage,
        data: fetchError.data,
      })
    }
    
    throw createError({
      statusCode: 502,
      statusMessage: 'Bad Gateway',
    })
  }
})
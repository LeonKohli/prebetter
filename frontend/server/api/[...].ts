import { joinURL } from 'ufo'

export default defineEventHandler(async (event) => {
  // Get the path from the event, which preserves trailing slashes
  const path = event.path.replace(/^\/api\//, '') // /api/users/ -> users/
  
  // Construct the full target URL
  const proxyUrl = useRuntimeConfig().apiBase
  const target = joinURL(proxyUrl, 'api/v1', path)
  
  // Get the current user session
  const session = await getUserSession(event)
  
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

  // Proxy the request to your backend
  return proxyRequest(event, target, {
    fetchOptions: {
      headers,
    }
  })
})
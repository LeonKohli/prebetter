import { joinURL } from 'ufo'

export default defineEventHandler(async (event) => {
  const { apiBase } = useRuntimeConfig()
  const path = event.context.params?._ ?? ''
  
  // Construct the full target URL
  const target = joinURL(apiBase, '/api/v1', path)

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
    // Do not forward cookies to the backend, as we are using token-based auth
    fetchOptions: {
      headers,
      redirect: 'manual' // Prevent following redirects automatically
    }
  })
})
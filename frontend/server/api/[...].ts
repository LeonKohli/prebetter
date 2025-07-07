import { joinURL } from 'ufo'

export default defineEventHandler(async (event) => {
    // Get the runtimeconfig proxy url
    const proxyUrl = useRuntimeConfig().public.apiBaseUrl
    // get the full path including /api
    const path = event.path
    const target = joinURL(proxyUrl, path)

    // proxy it!
    return proxyRequest(event, target)
})
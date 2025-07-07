export default defineEventHandler(async (event) => {
  // Clear the user session
  await clearUserSession(event)
  
  return { success: true }
})
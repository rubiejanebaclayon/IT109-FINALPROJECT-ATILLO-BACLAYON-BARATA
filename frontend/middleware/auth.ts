// Frontend role-based access control (RBAC).
// Usage in a page:  definePageMeta({ middleware: 'auth', roles: ['client'] })
// The backend enforces the SAME rules; this only gives a friendlier experience.
export default defineNuxtRouteMiddleware(async (to) => {
  const { user, ensureUser } = useAuth()
  const token = useCookie<string | null>('token')
  if (!token.value) return navigateTo('/login')
  await ensureUser()
  if (!user.value) return navigateTo('/login')
  const roles = to.meta.roles as string[] | undefined
  if (roles && !roles.includes(user.value.role)) return navigateTo('/dashboard')
})

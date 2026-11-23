export interface User {
  id: string
  email: string
  full_name: string
  avatar_url: string | null
  role: 'client' | 'freelancer' | 'admin'
}

export function useAuth() {
  const user = useState<User | null>('user', () => null)
  const { api, token } = useApi()

  async function ensureUser() {
    if (user.value || !token.value) return
    try {
      user.value = await api<User>('/auth/me')
    } catch {
      user.value = null
    }
  }

  async function logout() {
    token.value = null
    user.value = null
    await navigateTo('/login')
  }

  const isRole = (...roles: string[]) => !!user.value && roles.includes(user.value.role)

  return { user, ensureUser, logout, isRole }
}

// One place that talks to the FastAPI backend.
// - adds the JWT (Authorization: Bearer ...)
// - optionally adds the reCAPTCHA token (X-Captcha-Token)
// - turns backend errors into a readable Error message
interface ApiOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: any
  query?: Record<string, any>
  captcha?: string | null
}

function readableError(e: any): string {
  const detail = e?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    // FastAPI/Pydantic validation errors -> "field: message"
    return detail
      .map((d: any) => {
        const field = Array.isArray(d.loc) ? d.loc.filter((x: string) => x !== 'body').join('.') : ''
        const msg = String(d.msg || '').replace(/^Value error, /, '')
        return field ? `${field}: ${msg}` : msg
      })
      .join('; ')
  }
  if (e?.status === 429) return 'Too many requests. Please wait a moment and try again.'
  return e?.message || 'Something went wrong. Please try again.'
}

export function useApi() {
  const config = useRuntimeConfig()
  const token = useCookie<string | null>('token', { maxAge: 60 * 60 * 12, sameSite: 'strict' })

  async function api<T = any>(path: string, opts: ApiOptions = {}): Promise<T> {
    const headers: Record<string, string> = {}
    if (token.value) headers.Authorization = `Bearer ${token.value}`
    if (opts.captcha) headers['X-Captcha-Token'] = opts.captcha
    try {
      return await $fetch<T>(path, {
        baseURL: config.public.apiBase,
        method: opts.method || 'GET',
        body: opts.body,
        query: opts.query,
        headers,
      })
    } catch (e: any) {
      if (e?.status === 401 && token.value) {
        // Session expired or account disabled
        token.value = null
        useState('user').value = null
        await navigateTo('/login?error=session_expired')
      }
      throw new Error(readableError(e))
    }
  }

  return { api, token }
}

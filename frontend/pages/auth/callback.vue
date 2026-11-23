<script setup lang="ts">
// The backend redirects here as  /auth/callback#token=<JWT>
const { api, token } = useApi()
const { user } = useAuth()
const error = ref('')

onMounted(async () => {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  const t = params.get('token')
  history.replaceState(null, '', window.location.pathname) // remove the token from the address bar
  if (!t) return navigateTo('/login?error=oauth_failed')
  token.value = t
  try {
    user.value = await api('/auth/me')
    await navigateTo('/dashboard', { replace: true })
  } catch (e: any) {
    error.value = e.message
  }
})
</script>

<template>
  <p class="py-20 text-center text-muted-foreground">{{ error || 'Signing you in…' }}</p>
</template>

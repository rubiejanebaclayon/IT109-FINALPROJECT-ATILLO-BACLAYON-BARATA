<script setup lang="ts">
const config = useRuntimeConfig()
const route = useRoute()
const role = ref<'client' | 'freelancer'>('client')
const captcha = ref<string | null>(null)
const loading = ref(false)

const messages: Record<string, string> = {
  oauth_cancelled: 'Google sign-in was cancelled.',
  oauth_failed: 'Google sign-in failed. Please try again.',
  email_unverified: 'Your Google email is not verified.',
  domain_not_allowed: 'This email domain is not allowed.',
  account_disabled: 'Your account has been disabled. Contact the administrator.',
  session_expired: 'Your session expired. Please log in again.',
}
const error = computed(() => messages[String(route.query.error || '')] || '')

function login() {
  if (!captcha.value || loading.value) return
  loading.value = true
  const q = new URLSearchParams({ role: role.value, captcha_token: captcha.value })
  window.location.href = `${config.public.apiBase}/auth/google/login?${q}`
}
</script>

<template>
  <div class="mx-auto max-w-md py-6">
    <Card class="rounded-2xl border-slate-200/90 shadow-sm">
      <CardHeader>
        <CardTitle class="text-xl font-bold">Log in or sign up</CardTitle>
        <CardDescription>
          Continue with your Google account. New here? Pick how you will use the platform.
        </CardDescription>
      </CardHeader>

      <CardContent class="space-y-4">
        <p v-if="error" class="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {{ error }}
        </p>

        <!-- Role Selector with Clear Active State -->
        <fieldset class="grid grid-cols-2 gap-3">
          <label
            @click="role = 'client'"
            class="cursor-pointer rounded-xl border-2 p-3.5 text-sm transition select-none"
            :class="
              role === 'client'
                ? 'border-indigo-600 bg-indigo-50/70 shadow-2xs'
                : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
            "
          >
            <input v-model="role" type="radio" value="client" class="sr-only" />
            <div class="flex items-center justify-between">
              <strong class="text-slate-900">I need a service</strong>
              <span
                class="h-2.5 w-2.5 rounded-full transition"
                :class="role === 'client' ? 'bg-indigo-600' : 'bg-slate-200'"
              />
            </div>
            <span class="mt-1 block text-xs text-muted-foreground">Client (student or faculty)</span>
          </label>

          <label
            @click="role = 'freelancer'"
            class="cursor-pointer rounded-xl border-2 p-3.5 text-sm transition select-none"
            :class="
              role === 'freelancer'
                ? 'border-indigo-600 bg-indigo-50/70 shadow-2xs'
                : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
            "
          >
            <input v-model="role" type="radio" value="freelancer" class="sr-only" />
            <div class="flex items-center justify-between">
              <strong class="text-slate-900">I offer a service</strong>
              <span
                class="h-2.5 w-2.5 rounded-full transition"
                :class="role === 'freelancer' ? 'bg-indigo-600' : 'bg-slate-200'"
              />
            </div>
            <span class="mt-1 block text-xs text-muted-foreground">Freelancer (student)</span>
          </label>
        </fieldset>

        <p class="text-xs text-muted-foreground">The choice only applies to new accounts.</p>

        <Recaptcha @verified="captcha = $event" @expired="captcha = null" />

        <Button
          type="button"
          class="w-full cursor-pointer"
          :disabled="!captcha || loading"
          @click="login"
        >
          {{ loading ? 'Redirecting to Google...' : 'Continue with Google' }}
        </Button>
      </CardContent>
    </Card>
  </div>
</template>
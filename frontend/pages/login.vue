
<script setup lang="ts">
const config = useRuntimeConfig()
const route = useRoute()

const { api, token } = useApi()
const { user } = useAuth()

type Role = 'client' | 'freelancer'
type AuthMode = 'login' | 'register'

const mode = ref<AuthMode>('login')
const role = ref<Role>('client')
const captcha = ref<string | null>(null)
const loading = ref(false)
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const formError = ref('')
const successMessage = ref('')

const form = reactive({
  username: '',
  full_name: '',
  email: '',
  password: '',
  confirm_password: '',
})

const messages: Record<string, string> = {
  oauth_cancelled: 'Google sign-in was cancelled.',
  oauth_failed: 'Google sign-in failed. Please try again.',
  email_unverified: 'Your Google email is not verified.',
  domain_not_allowed: 'This email domain is not allowed.',
  account_disabled: 'Your account has been disabled. Contact the administrator.',
  session_expired: 'Your session expired. Please log in again.',
}

const error = computed(
  () => messages[String(route.query.error || '')] || '',
)

function switchMode(newMode: AuthMode) {
  mode.value = newMode
  formError.value = ''
  successMessage.value = ''
  captcha.value = null

  form.username = ''
  form.full_name = ''
  form.email = ''
  form.password = ''
  form.confirm_password = ''
}

function googleLogin() {
  if (!captcha.value || loading.value) return

  loading.value = true

  const q = new URLSearchParams({
    role: role.value,
    captcha_token: captcha.value,
  })

  window.location.href =
    `${config.public.apiBase}/auth/google/login?${q}`
}

async function submitForm() {
  if (!captcha.value || loading.value) return

  loading.value = true
  formError.value = ''
  successMessage.value = ''

  try {
    const endpoint =
      mode.value === 'register'
        ? '/auth/register'
        : '/auth/login'

    const body =
      mode.value === 'register'
        ? {
            username: form.username,
            full_name: form.full_name,
            email: form.email,
            password: form.password,
            confirm_password: form.confirm_password,
            role: role.value,
          }
        : {
            username: form.username,
            password: form.password,
          }

    const response = await api<{
      access_token: string
      token_type: string
      user: {
        id: string
        email: string
        full_name: string
        avatar_url: string | null
        role: Role | 'admin'
      }
    }>(endpoint, {
      method: 'POST',
      body,
      captcha: captcha.value,
    })

    token.value = response.access_token
    user.value = response.user

    captcha.value = null

    await navigateTo('/dashboard', { replace: true })
  } catch (e: any) {
    formError.value = e.message || 'Something went wrong. Please try again.'
    captcha.value = null
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-md py-6">
    <Card class="rounded-2xl border-slate-200/90 shadow-sm">

      <CardHeader>
        <CardTitle class="text-xl font-bold text-[#3D2630]">
          {{ mode === 'login' ? 'Welcome Back' : 'Create Your Account' }}
        </CardTitle>

        <CardDescription>
          {{
            mode === 'login'
              ? 'Log in to your Student Gig & Skill Marketplace account.'
              : 'Join the marketplace and connect with other students.'
          }}
        </CardDescription>
      </CardHeader>

      <CardContent class="space-y-4">

        <!-- Existing Google OAuth errors -->
        <p
          v-if="error"
          class="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
        >
          {{ error }}
        </p>

        <!-- Form errors -->
        <p
          v-if="formError"
          class="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
        >
          {{ formError }}
        </p>

        <p
          v-if="successMessage"
          class="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700"
        >
          {{ successMessage }}
        </p>

        <!-- Login / Register tabs -->
        <div class="grid grid-cols-2 rounded-xl bg-[#F7EEF1] p-1">
          <button
            type="button"
            @click="switchMode('login')"
            class="rounded-lg px-4 py-2 text-sm font-semibold transition"
            :class="
              mode === 'login'
                ? 'bg-[#641A32] text-white shadow-sm'
                : 'text-[#641A32] hover:bg-white/70'
            "
          >
            Log In
          </button>

          <button
            type="button"
            @click="switchMode('register')"
            class="rounded-lg px-4 py-2 text-sm font-semibold transition"
            :class="
              mode === 'register'
                ? 'bg-[#641A32] text-white shadow-sm'
                : 'text-[#641A32] hover:bg-white/70'
            "
          >
            Register
          </button>
        </div>

        <!-- Registration fields -->
        <template v-if="mode === 'register'">

          <div class="space-y-1.5">
            <label class="text-sm font-medium text-[#3D2630]">
              Full Name
            </label>
            <input
              v-model="form.full_name"
              type="text"
              placeholder="Enter your full name"
              autocomplete="name"
              required
              maxlength="100"
              class="w-full rounded-lg border border-[#E8DADD] px-3 py-2.5 text-sm outline-none transition focus:border-[#641A32] focus:ring-2 focus:ring-[#641A32]/10"
            />
          </div>

          <div class="space-y-1.5">
            <label class="text-sm font-medium text-[#3D2630]">
              Email Address
            </label>
            <input
              v-model="form.email"
              type="email"
              placeholder="student@example.com"
              autocomplete="email"
              required
              class="w-full rounded-lg border border-[#E8DADD] px-3 py-2.5 text-sm outline-none transition focus:border-[#641A32] focus:ring-2 focus:ring-[#641A32]/10"
            />
          </div>

        </template>

        <!-- Username -->
        <div class="space-y-1.5">
          <label class="text-sm font-medium text-[#3D2630]">
            Username
          </label>
          <input
            v-model="form.username"
            type="text"
            placeholder="Enter your username"
            autocomplete="username"
            required
            minlength="4"
            maxlength="20"
            class="w-full rounded-lg border border-[#E8DADD] px-3 py-2.5 text-sm outline-none transition focus:border-[#641A32] focus:ring-2 focus:ring-[#641A32]/10"
          />
          <p class="text-xs text-muted-foreground">
            Use 4–20 letters, numbers, or underscores.
          </p>
        </div>

        <!-- Password -->
        <div class="space-y-1.5">
          <label class="text-sm font-medium text-[#3D2630]">
            Password
          </label>

          <div class="relative">
            <input
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="Enter your password"
              :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
              required
              minlength="8"
              maxlength="64"
              class="w-full rounded-lg border border-[#E8DADD] px-3 py-2.5 pr-16 text-sm outline-none transition focus:border-[#641A32] focus:ring-2 focus:ring-[#641A32]/10"
            />

            <button
              type="button"
              @click="showPassword = !showPassword"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-medium text-[#641A32]"
            >
              {{ showPassword ? 'Hide' : 'Show' }}
            </button>
          </div>

          <p
            v-if="mode === 'register'"
            class="text-xs text-muted-foreground"
          >
            Must contain uppercase and lowercase letters, a number, and a special character.
          </p>
        </div>

        <!-- Confirm Password -->
        <div v-if="mode === 'register'" class="space-y-1.5">
          <label class="text-sm font-medium text-[#3D2630]">
            Confirm Password
          </label>

          <div class="relative">
            <input
              v-model="form.confirm_password"
              :type="showConfirmPassword ? 'text' : 'password'"
              placeholder="Confirm your password"
              autocomplete="new-password"
              required
              maxlength="64"
              class="w-full rounded-lg border border-[#E8DADD] px-3 py-2.5 pr-16 text-sm outline-none transition focus:border-[#641A32] focus:ring-2 focus:ring-[#641A32]/10"
            />

            <button
              type="button"
              @click="showConfirmPassword = !showConfirmPassword"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-medium text-[#641A32]"
            >
              {{ showConfirmPassword ? 'Hide' : 'Show' }}
            </button>
          </div>
        </div>

        <!-- Role selector: registration only -->
        <template v-if="mode === 'register'">
          <div class="space-y-2">
            <p class="text-sm font-medium text-[#3D2630]">
              How will you use the platform?
            </p>

            <fieldset class="grid grid-cols-2 gap-3">
              <label
                @click="role = 'client'"
                class="cursor-pointer rounded-xl border-2 p-3.5 text-sm transition select-none"
                :class="
                  role === 'client'
                    ? 'border-[#641A32] bg-[#F7EEF1] shadow-sm'
                    : 'border-[#E8DADD] bg-white hover:border-[#8A4057] hover:bg-[#FBF7F8]'
                "
              >
                <input
                  v-model="role"
                  type="radio"
                  value="client"
                  class="sr-only"
                />
                <strong class="text-[#3D2630]">
                  I need a service
                </strong>
                <span class="mt-1 block text-xs text-muted-foreground">
                  Client
                </span>
              </label>

              <label
                @click="role = 'freelancer'"
                class="cursor-pointer rounded-xl border-2 p-3.5 text-sm transition select-none"
                :class="
                  role === 'freelancer'
                    ? 'border-[#641A32] bg-[#F7EEF1] shadow-sm'
                    : 'border-[#E8DADD] bg-white hover:border-[#8A4057] hover:bg-[#FBF7F8]'
                "
              >
                <input
                  v-model="role"
                  type="radio"
                  value="freelancer"
                  class="sr-only"
                />
                <strong class="text-[#3D2630]">
                  I offer a service
                </strong>
                <span class="mt-1 block text-xs text-muted-foreground">
                  Freelancer
                </span>
              </label>
            </fieldset>
          </div>
        </template>

        <!-- CAPTCHA remains enabled for both methods -->
        <Recaptcha
          @verified="captcha = $event"
          @expired="captcha = null"
        />

        <!-- Username/password submit -->
        <Button
          type="button"
          class="w-full cursor-pointer bg-[#641A32] text-white hover:bg-[#4D1427]"
          :disabled="!captcha || loading"
          @click="submitForm"
        >
          {{
            loading
              ? 'Please wait...'
              : mode === 'login'
                ? 'Log In'
                : 'Create Account'
          }}
        </Button>

        <!-- Google OAuth -->
        <div class="relative py-2">
          <div class="absolute inset-0 flex items-center">
            <span class="w-full border-t border-[#E8DADD]"></span>
          </div>
          <div class="relative flex justify-center">
            <span class="bg-white px-3 text-xs text-muted-foreground">
              OR
            </span>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          class="w-full cursor-pointer border-[#E8DADD] text-[#3D2630] hover:bg-[#FBF7F8]"
          :disabled="!captcha || loading"
          @click="googleLogin"
        >
          Continue with Google
        </Button>

        <p class="text-center text-xs text-muted-foreground">
          {{
            mode === 'login'
              ? "Don't have an account? Select Register above."
              : 'Already have an account? Select Log In above.'
          }}
        </p>

      </CardContent>
    </Card>
  </div>
</template>

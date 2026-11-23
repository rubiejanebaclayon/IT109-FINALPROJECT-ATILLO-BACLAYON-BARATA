<script setup lang="ts">
// Google reCAPTCHA v2 checkbox. Emits the token when solved.
// Tokens are single-use: call reset() (via ref) after every submit.
const emit = defineEmits<{ (e: 'verified', token: string): void; (e: 'expired'): void }>()
const config = useRuntimeConfig()
const el = ref<HTMLElement | null>(null)
let widgetId: number | null = null

function renderWidget() {
  const g = (window as any).grecaptcha
  if (!el.value || !g?.render || widgetId !== null) return
  widgetId = g.render(el.value, {
    sitekey: config.public.recaptchaSiteKey,
    callback: (t: string) => emit('verified', t),
    'expired-callback': () => emit('expired'),
  })
}

onMounted(() => {
  const w = window as any
  if (w.grecaptcha?.render) return renderWidget()
  w.__onRecaptchaLoad = renderWidget
  if (!document.getElementById('recaptcha-script')) {
    const s = document.createElement('script')
    s.id = 'recaptcha-script'
    s.src = 'https://www.google.com/recaptcha/api.js?onload=__onRecaptchaLoad&render=explicit'
    s.async = true
    document.head.appendChild(s)
  }
})

function reset() {
  const g = (window as any).grecaptcha
  if (g && widgetId !== null) g.reset(widgetId)
  emit('expired')
}
defineExpose({ reset })
</script>

<template>
  <div ref="el" />
</template>

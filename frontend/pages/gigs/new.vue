<script setup lang="ts">
definePageMeta({ middleware: 'auth', roles: ['client'] })
const { api } = useApi()
const busy = ref(false)
const error = ref('')
const form = ref<{ resetCaptcha: () => void } | null>(null)

async function create({ body, captcha }: { body: any; captcha: string | null }) {
  busy.value = true
  error.value = ''
  try {
    await api('/gigs', { method: 'POST', body, captcha })
    await navigateTo('/my/gigs?created=1')
  } catch (e: any) {
    error.value = e.message
    form.value?.resetCaptcha()
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-2xl">
    <Card>
      <CardHeader>
        <CardTitle>Post a gig request</CardTitle>
        <CardDescription>An administrator reviews every gig before freelancers can see it.</CardDescription>
      </CardHeader>
      <CardContent>
        <p v-if="error" class="mb-3 rounded-md bg-red-50 p-2 text-sm text-red-700">{{ error }}</p>
        <GigForm ref="form" submit-label="Submit for approval" use-captcha :busy="busy" @submit="create" />
      </CardContent>
    </Card>
  </div>
</template>

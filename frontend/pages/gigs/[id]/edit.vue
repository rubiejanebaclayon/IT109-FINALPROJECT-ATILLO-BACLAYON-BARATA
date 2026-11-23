<script setup lang="ts">
definePageMeta({ middleware: 'auth', roles: ['client'] })
const route = useRoute()
const { api } = useApi()
const id = String(route.params.id)
const gig = await api<any>(`/gigs/${id}`).catch(() => null)
const busy = ref(false)
const error = ref('')

async function save({ body }: { body: any }) {
  busy.value = true
  error.value = ''
  try {
    await api(`/gigs/${id}`, { method: 'PUT', body })
    await navigateTo('/my/gigs?updated=1')
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-2xl">
    <p v-if="!gig" class="text-muted-foreground">Gig not found.</p>
    <Card v-else>
      <CardHeader>
        <CardTitle>Edit gig</CardTitle>
        <CardDescription>Saving sends the gig back to the administrator for approval.</CardDescription>
      </CardHeader>
      <CardContent>
        <p v-if="error" class="mb-3 rounded-md bg-red-50 p-2 text-sm text-red-700">{{ error }}</p>
        <GigForm :initial="gig" submit-label="Save changes" :busy="busy" @submit="save" />
      </CardContent>
    </Card>
  </div>
</template>

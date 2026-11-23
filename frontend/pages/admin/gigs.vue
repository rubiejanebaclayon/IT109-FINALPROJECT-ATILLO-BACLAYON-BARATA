<script setup lang="ts">
definePageMeta({ middleware: 'auth', roles: ['admin'] })
const { api } = useApi()
const status = ref('pending_approval')
const { data: gigs, pending, refresh } = await useAsyncData('admin-gigs',
  () => api<any[]>('/admin/gigs', { query: { status: status.value } }), { watch: [status] })
const error = ref('')
const msg = ref('')

async function approve(g: any) {
  error.value = msg.value = ''
  try {
    await api(`/admin/gigs/${g.id}/approve`, { method: 'POST' })
    msg.value = `Approved "${g.title}".`
    await refresh()
  } catch (e: any) { error.value = e.message }
}
async function reject(g: any) {
  const reason = window.prompt('Reason for rejection (shown to the client):')
  if (!reason) return
  error.value = msg.value = ''
  try {
    await api(`/admin/gigs/${g.id}/reject`, { method: 'POST', body: { reason } })
    msg.value = `Rejected "${g.title}".`
    await refresh()
  } catch (e: any) { error.value = e.message }
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-bold">Gig approvals</h1>
      <div class="w-56">
        <AppSelect v-model="status">
          <option value="pending_approval">Pending approval</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="awarded">Awarded</option>
          <option value="closed">Closed</option>
          <option value="all">All</option>
        </AppSelect>
      </div>
    </div>
    <p v-if="msg" class="rounded-md bg-emerald-50 p-2 text-sm text-emerald-700">{{ msg }}</p>
    <p v-if="error" class="rounded-md bg-red-50 p-2 text-sm text-red-700">{{ error }}</p>

    <p v-if="pending && !gigs" class="text-muted-foreground">Loading…</p>
    <p v-else-if="!gigs?.length" class="rounded-xl border bg-background p-8 text-center text-muted-foreground">Nothing here.</p>

    <div class="space-y-3">
      <Card v-for="g in gigs" :key="g.id">
        <CardHeader class="pb-2">
          <div class="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{{ g.category }}</Badge><StatusBadge :status="g.status" />
          </div>
          <CardTitle class="text-base">
            <NuxtLink :to="`/gigs/${g.id}`" class="hover:underline">{{ g.title }}</NuxtLink>
          </CardTitle>
          <CardDescription>{{ g.client_name }} ({{ g.client_email }}) · {{ fdate(g.created_at) }}</CardDescription>
        </CardHeader>
        <CardContent class="space-y-2 text-sm">
          <p class="whitespace-pre-line">{{ g.description }}</p>
          <p class="font-medium">{{ peso(g.budget_min) }} – {{ peso(g.budget_max) }} · due {{ fdate(g.deadline) }}</p>
          <p v-if="g.admin_note" class="text-xs text-red-700">Reason: {{ g.admin_note }}</p>
          <div v-if="g.status === 'pending_approval'" class="flex gap-2 pt-1">
            <Button size="sm" @click="approve(g)">Approve</Button>
            <Button size="sm" variant="destructive" @click="reject(g)">Reject</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
// Manual payouts: the admin sends the money OUTSIDE the app (GCash, bank...) and records it here.
definePageMeta({ middleware: 'auth', roles: ['admin'] })
const { api } = useApi()
const status = ref('all')
const { data: payouts, pending, refresh } = await useAsyncData('admin-payouts',
  () => api<any[]>('/admin/payouts', { query: { status: status.value } }), { watch: [status] })

const drafts = reactive<Record<string, { status: string; method: string; reference_no: string; admin_note: string }>>({})
watch(payouts, (list) => {
  for (const p of list || []) {
    if (!drafts[p.id]) drafts[p.id] = { status: p.status, method: p.method || '', reference_no: p.reference_no || '', admin_note: p.admin_note || '' }
  }
}, { immediate: true })

const error = ref('')
const msg = ref('')
async function save(p: any) {
  const d = drafts[p.id]
  error.value = msg.value = ''
  try {
    await api(`/admin/payouts/${p.id}`, {
      method: 'PUT',
      body: { status: d.status, method: d.method || null, reference_no: d.reference_no || null, admin_note: d.admin_note || null },
    })
    msg.value = `Payout for "${p.gig_title}" updated.`
    delete drafts[p.id]
    await refresh()
  } catch (e: any) { error.value = e.message }
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Payouts</h1>
        <p class="text-sm text-muted-foreground">Send the net amount to the freelancer yourself, then record it here.</p>
      </div>
      <div class="w-48">
        <AppSelect v-model="status">
          <option value="all">All</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="paid">Paid</option>
          <option value="failed">Failed</option>
        </AppSelect>
      </div>
    </div>
    <p v-if="msg" class="rounded-md bg-emerald-50 p-2 text-sm text-emerald-700">{{ msg }}</p>
    <p v-if="error" class="rounded-md bg-red-50 p-2 text-sm text-red-700">{{ error }}</p>
    <p v-if="pending && !payouts" class="text-muted-foreground">Loading…</p>
    <p v-else-if="!payouts?.length" class="rounded-xl border bg-background p-8 text-center text-muted-foreground">No payouts.</p>

    <div class="space-y-3">
      <Card v-for="p in payouts" :key="p.id">
        <CardHeader class="pb-2">
          <CardTitle class="text-base">
            <NuxtLink :to="`/contracts/${p.contract_id}`" class="hover:underline">{{ p.gig_title }}</NuxtLink>
            <StatusBadge :status="p.status" class="ml-2 align-middle" />
          </CardTitle>
          <CardDescription>
            {{ p.freelancer_name }} ({{ p.freelancer_email }}) · Gross {{ peso(p.gross_amount) }} − fee {{ peso(p.platform_fee) }} =
            <strong>{{ peso(p.net_amount) }}</strong>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p v-if="p.status === 'paid'" class="text-sm text-muted-foreground">
            Paid via {{ p.method }} · ref {{ p.reference_no }} · {{ fdatetime(p.paid_at) }}
          </p>
          <form v-else-if="drafts[p.id]" class="grid gap-3 sm:grid-cols-5" @submit.prevent="save(p)">
            <AppSelect v-model="drafts[p.id].status">
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="paid">Paid</option>
              <option value="failed">Failed</option>
            </AppSelect>
            <Input v-model="drafts[p.id].method" placeholder="Method (GCash, bank…)" maxlength="40" />
            <Input v-model="drafts[p.id].reference_no" placeholder="Reference no." maxlength="60" />
            <Input v-model="drafts[p.id].admin_note" placeholder="Note (optional)" maxlength="500" />
            <Button type="submit">Save</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

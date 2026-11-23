<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
const route = useRoute()
const { api } = useApi()
const { user } = useAuth()
const id = String(route.params.id)

const { data: c, error: loadError, refresh } = await useAsyncData(`contract-${id}`, () => api<any>(`/contracts/${id}`))
const { data: thread, refresh: refreshThread } = await useAsyncData(`thread-${id}`,
  () => api<any[]>(`/contracts/${id}/thread`).catch(() => []))

const isClient = computed(() => c.value?.client_id === user.value?.id)
const isFreelancer = computed(() => c.value?.freelancer_id === user.value?.id)
const msg = ref('')
const error = ref('')
const busy = ref(false)

const steps = [
  ['pending_payment', 'Awaiting payment'],
  ['funded', 'Funded (escrow)'],
  ['submitted', 'Work submitted'],
  ['approved', 'Approved'],
  ['paid_out', 'Paid out'],
]
const stepIndex = computed(() => steps.findIndex((s) => s[0] === c.value?.status))

async function run(label: string, fn: () => Promise<any>, done = '') {
  busy.value = true
  error.value = msg.value = ''
  try {
    await fn()
    if (done) msg.value = done
    await refresh()
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

// ---- payment ----
async function pay() {
  busy.value = true
  error.value = ''
  try {
    const r = await api<{ checkout_url: string }>(`/contracts/${id}/pay`, { method: 'POST' })
    window.location.href = r.checkout_url // PayMongo hosted checkout (test mode)
  } catch (e: any) {
    error.value = e.message
    busy.value = false
  }
}
const syncPayment = () => run('sync', () => api(`/contracts/${id}/sync-payment`, { method: 'POST' }), 'Payment status refreshed.')

// When PayMongo sends the client back with ?paid=1, check the payment right away.
onMounted(async () => {
  if (route.query.paid === '1' && isClient.value && c.value?.status === 'pending_payment') {
    await syncPayment()
    await navigateTo(`/contracts/${id}`, { replace: true })
  }
})

const cancel = () => confirm('Cancel this contract? Only possible before payment.') &&
  run('cancel', () => api(`/contracts/${id}/cancel`, { method: 'POST' }), 'Contract cancelled.')
const approve = () => confirm('Approve the work? This releases the payout request to the administrator.') &&
  run('approve', () => api(`/contracts/${id}/approve`, { method: 'POST' }), 'Work approved. The administrator will send the payout.')

// ---- submit work (external link) ----
const sub = reactive({ link_url: '', notes: '' })
async function submitWork() {
  await run('submit', () => api(`/contracts/${id}/submit`, { method: 'POST', body: { ...sub, notes: sub.notes || null } }),
    'Work submitted. The client has been notified.')
  if (!error.value) Object.assign(sub, { link_url: '', notes: '' })
}

// ---- Gig Ticket Thread ----
const reply = ref('')
async function send() {
  if (!reply.value.trim()) return
  try {
    await api(`/contracts/${id}/thread`, { method: 'POST', body: { body: reply.value } })
    reply.value = ''
    await refreshThread()
  } catch (e: any) {
    error.value = e.message
  }
}
</script>

<template>
  <p v-if="loadError || !c" class="py-10 text-center text-muted-foreground">Contract not found.</p>

  <div v-else class="grid gap-6 lg:grid-cols-3">
    <div class="space-y-6 lg:col-span-2">
      <Card>
        <CardHeader>
          <CardTitle class="text-xl">{{ c.gig_title }}</CardTitle>
          <CardDescription>
            Client: {{ c.client_name }} · Freelancer:
            <NuxtLink :to="`/profiles/${c.freelancer_id}`" class="underline">{{ c.freelancer_name }}</NuxtLink>
          </CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <p class="text-lg font-semibold">{{ peso(c.amount) }} <StatusBadge :status="c.status" class="ml-2 align-middle" /></p>

          <ol v-if="c.status !== 'cancelled'" class="grid grid-cols-5 gap-1 text-center text-[11px]">
            <li v-for="(s, i) in steps" :key="s[0]" class="rounded-md px-1 py-2"
              :class="i <= stepIndex ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'">
              {{ s[1] }}
            </li>
          </ol>

          <p v-if="msg" class="rounded-md bg-emerald-50 p-2 text-sm text-emerald-700">{{ msg }}</p>
          <p v-if="error" class="rounded-md bg-red-50 p-2 text-sm text-red-700">{{ error }}</p>

          <!-- Client actions -->
          <div v-if="isClient && c.status === 'pending_payment'" class="space-y-2 rounded-lg border p-3">
            <p class="text-sm">Prepay into escrow to start the work. Sandbox mode: use PayMongo test card/e-wallet details.</p>
            <div class="flex flex-wrap gap-2">
              <Button :disabled="busy" @click="pay">Pay {{ peso(c.amount) }} with PayMongo</Button>
              <Button v-if="c.payment" variant="outline" :disabled="busy" @click="syncPayment">I already paid – refresh status</Button>
              <Button variant="ghost" :disabled="busy" @click="cancel">Cancel contract</Button>
            </div>
          </div>

          <div v-if="isClient && c.status === 'submitted'" class="rounded-lg border p-3">
            <p class="mb-2 text-sm">The freelancer submitted the work. Review it, then approve.</p>
            <Button :disabled="busy" @click="approve">Approve work</Button>
          </div>

          <p v-if="isFreelancer && c.status === 'pending_payment'" class="text-sm text-muted-foreground">
            Waiting for the client to fund the escrow. Start working once the status becomes Funded.
          </p>
          <p v-if="c.status === 'approved'" class="text-sm text-muted-foreground">
            Approved. Waiting for the administrator to send and record the payout.
          </p>

          <!-- Freelancer: submit deliverable link -->
          <form v-if="isFreelancer && ['funded', 'submitted'].includes(c.status)" class="space-y-3 rounded-lg border p-3"
            @submit.prevent="submitWork">
            <p class="text-sm font-medium">{{ c.status === 'submitted' ? 'Submit a new version' : 'Submit completed work' }}</p>
            <div class="space-y-1.5">
              <Label for="link">Link to the deliverable (https)</Label>
              <Input id="link" v-model="sub.link_url" type="url" required placeholder="https://drive.google.com/…" />
              <p class="text-xs text-muted-foreground">Share the file with “anyone with the link can view” (e.g. Google Drive).</p>
            </div>
            <div class="space-y-1.5">
              <Label for="notes">Notes (optional)</Label>
              <Textarea id="notes" v-model="sub.notes" rows="3" maxlength="1000" />
            </div>
            <Button type="submit" :disabled="busy">Submit work</Button>
          </form>
        </CardContent>
      </Card>

      <Card v-if="c.submissions?.length">
        <CardHeader><CardTitle class="text-lg">Submissions</CardTitle></CardHeader>
        <CardContent class="space-y-2 text-sm">
          <div v-for="s in c.submissions" :key="s.id" class="rounded-lg border p-3">
            <a :href="s.link_url" target="_blank" rel="noopener noreferrer nofollow" class="break-all text-primary underline">{{ s.link_url }}</a>
            <p v-if="s.notes" class="mt-1 text-muted-foreground">{{ s.notes }}</p>
            <p class="mt-1 text-xs text-muted-foreground">{{ fdatetime(s.created_at) }}</p>
          </div>
        </CardContent>
      </Card>

      <!-- Gig Ticket Thread -->
      <Card v-if="c.status !== 'cancelled'">
        <CardHeader class="flex-row items-center justify-between space-y-0">
          <CardTitle class="text-lg">Gig ticket thread</CardTitle>
          <Button variant="ghost" size="sm" @click="refreshThread()">Refresh</Button>
        </CardHeader>
        <CardContent class="space-y-3">
          <p v-if="!thread?.length" class="text-sm text-muted-foreground">No messages yet. Use this thread for questions about the gig.</p>
          <div v-for="m in thread" :key="m.id" class="rounded-lg p-3 text-sm"
            :class="m.sender_id === user?.id ? 'ml-8 bg-primary/10' : 'mr-8 bg-muted'">
            <p class="text-xs font-medium">{{ m.sender_name }} <span class="font-normal text-muted-foreground capitalize">({{ m.sender_role }}) · {{ fdatetime(m.created_at) }}</span></p>
            <p class="mt-1 whitespace-pre-line">{{ m.body }}</p>
          </div>
          <form class="flex gap-2" @submit.prevent="send">
            <Textarea v-model="reply" rows="2" maxlength="2000" placeholder="Write a message…" class="flex-1" />
            <Button type="submit" :disabled="!reply.trim()">Send</Button>
          </form>
        </CardContent>
      </Card>
    </div>

    <!-- Side panel: money -->
    <div class="space-y-4">
      <Card>
        <CardHeader><CardTitle class="text-base">Payment (escrow)</CardTitle></CardHeader>
        <CardContent class="space-y-1 text-sm">
          <p v-if="!c.payment" class="text-muted-foreground">No payment started.</p>
          <template v-else>
            <p>Status: <StatusBadge :status="c.payment.status" /></p>
            <p>Amount: {{ peso(c.payment.amount) }}</p>
            <p v-if="c.payment.paid_at">Paid: {{ fdatetime(c.payment.paid_at) }}</p>
          </template>
        </CardContent>
      </Card>

      <Card v-if="c.payout && (isFreelancer || user?.role === 'admin')">
        <CardHeader><CardTitle class="text-base">Payout</CardTitle></CardHeader>
        <CardContent class="space-y-1 text-sm">
          <p>Status: <StatusBadge :status="c.payout.status" /></p>
          <p>Gross: {{ peso(c.payout.gross_amount) }}</p>
          <p>Platform fee: {{ peso(c.payout.platform_fee) }}</p>
          <p class="font-medium">You receive: {{ peso(c.payout.net_amount) }}</p>
          <template v-if="c.payout.status === 'paid'">
            <p>Method: {{ c.payout.method }}</p>
            <p>Reference: {{ c.payout.reference_no }}</p>
            <p>Paid: {{ fdatetime(c.payout.paid_at) }}</p>
          </template>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

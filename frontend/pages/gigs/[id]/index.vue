<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
const route = useRoute()
const { api } = useApi()
const { user } = useAuth()
const id = String(route.params.id)

const { data: gig, error: loadError, refresh } = await useAsyncData(`gig-${id}`, () => api<any>(`/gigs/${id}`))
const isOwner = computed(() => gig.value?.client_id === user.value?.id)
const canSeeBids = computed(() => isOwner.value || user.value?.role === 'admin')
const { data: bids, refresh: refreshBids } = await useAsyncData(`gig-bids-${id}`,
  () => (canSeeBids.value ? api<any[]>(`/gigs/${id}/bids`) : Promise.resolve([])))

const msg = ref('')
const error = ref('')
const busy = ref(false)

// ----- freelancer: place / edit a bid -----
const bidForm = reactive({ amount: 100, delivery_days: 3, proposal: '' })
const captcha = ref<string | null>(null)
const captchaRef = ref<{ reset: () => void } | null>(null)
const editing = ref(false)

function startEdit() {
  Object.assign(bidForm, {
    amount: Number(gig.value.my_bid.amount),
    delivery_days: gig.value.my_bid.delivery_days,
    proposal: gig.value.my_bid.proposal,
  })
  editing.value = true
}

async function submitBid() {
  busy.value = true
  error.value = msg.value = ''
  try {
    const body = { amount: Number(bidForm.amount), delivery_days: Number(bidForm.delivery_days), proposal: bidForm.proposal }
    if (editing.value) await api(`/bids/${gig.value.my_bid.id}`, { method: 'PUT', body })
    else await api(`/gigs/${id}/bids`, { method: 'POST', body, captcha: captcha.value })
    msg.value = editing.value ? 'Bid updated.' : 'Bid submitted!'
    editing.value = false
    await refresh()
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = false
    captchaRef.value?.reset()
  }
}

async function withdraw() {
  if (!confirm('Withdraw your bid?')) return
  try {
    await api(`/bids/${gig.value.my_bid.id}`, { method: 'DELETE' })
    msg.value = 'Bid withdrawn.'
    await refresh()
  } catch (e: any) {
    error.value = e.message
  }
}

// ----- client: accept a bid -----
async function accept(bidId: string) {
  if (!confirm('Select this freelancer? Other pending bids will be declined.')) return
  error.value = ''
  try {
    const contract = await api<any>(`/bids/${bidId}/accept`, { method: 'POST' })
    await navigateTo(`/contracts/${contract.id}`)
  } catch (e: any) {
    error.value = e.message
  }
}

async function deleteGig() {
  if (!confirm('Delete this gig permanently?')) return
  try {
    await api(`/gigs/${id}`, { method: 'DELETE' })
    await navigateTo(user.value?.role === 'admin' ? '/admin/gigs' : '/my/gigs')
  } catch (e: any) {
    error.value = e.message
  }
}
</script>

<template>
  <p v-if="loadError || !gig" class="py-10 text-center text-muted-foreground">Gig not found.</p>

  <div v-else class="grid gap-6 lg:grid-cols-3">
    <div class="space-y-6 lg:col-span-2">
      <Card>
        <CardHeader>
          <div class="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{{ gig.category }}</Badge>
            <StatusBadge :status="gig.status" />
          </div>
          <CardTitle class="text-xl">{{ gig.title }}</CardTitle>
          <CardDescription>Posted by {{ gig.client_name }} · due {{ fdate(gig.deadline) }}</CardDescription>
        </CardHeader>
        <CardContent class="space-y-3">
          <p class="whitespace-pre-line text-sm">{{ gig.description }}</p>
          <p class="font-medium">Budget: {{ peso(gig.budget_min) }} – {{ peso(gig.budget_max) }}</p>
          <p class="text-sm text-muted-foreground">{{ gig.bid_count }} bid{{ gig.bid_count === 1 ? '' : 's' }}</p>
          <p v-if="gig.admin_note" class="rounded-md bg-red-50 p-2 text-sm text-red-700">Admin note: {{ gig.admin_note }}</p>

          <div v-if="isOwner && ['pending_approval', 'approved', 'rejected'].includes(gig.status)" class="flex gap-2 pt-2">
            <Button variant="outline" size="sm" as-child><NuxtLink :to="`/gigs/${id}/edit`">Edit</NuxtLink></Button>
            <Button variant="destructive" size="sm" @click="deleteGig">Delete</Button>
          </div>
          <Button v-if="user?.role === 'admin' && gig.status !== 'awarded'" variant="destructive" size="sm" @click="deleteGig">
            Delete (admin)
          </Button>
        </CardContent>
      </Card>

      <p v-if="msg" class="rounded-md bg-emerald-50 p-2 text-sm text-emerald-700">{{ msg }}</p>
      <p v-if="error" class="rounded-md bg-red-50 p-2 text-sm text-red-700">{{ error }}</p>

      <!-- Client / admin: bids list -->
      <Card v-if="canSeeBids">
        <CardHeader><CardTitle class="text-lg">Bids ({{ bids?.length || 0 }})</CardTitle></CardHeader>
        <CardContent class="space-y-3">
          <p v-if="!bids?.length" class="text-sm text-muted-foreground">No bids yet.</p>
          <div v-for="b in bids" :key="b.id" class="rounded-lg border p-3">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <NuxtLink :to="`/profiles/${b.freelancer_id}`" class="font-medium hover:underline">{{ b.freelancer_name }}</NuxtLink>
              <StatusBadge :status="b.status" />
            </div>
            <p v-if="b.headline" class="text-xs text-muted-foreground">{{ b.headline }}</p>
            <p class="mt-2 text-sm font-medium">{{ peso(b.amount) }} · {{ b.delivery_days }} day{{ b.delivery_days === 1 ? '' : 's' }}</p>
            <p class="mt-1 whitespace-pre-line text-sm text-muted-foreground">{{ b.proposal }}</p>
            <div v-if="b.skills?.length" class="mt-2 flex flex-wrap gap-1">
              <Badge v-for="s in b.skills" :key="s" variant="outline">{{ s }}</Badge>
            </div>
            <Button v-if="isOwner && gig.status === 'approved' && b.status === 'pending'" size="sm" class="mt-3" @click="accept(b.id)">
              Select this freelancer
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Freelancer: bid panel -->
    <div v-if="user?.role === 'freelancer'" class="space-y-4">
      <Card v-if="gig.my_bid && !editing">
        <CardHeader><CardTitle class="text-lg">Your bid</CardTitle></CardHeader>
        <CardContent class="space-y-2 text-sm">
          <StatusBadge :status="gig.my_bid.status" />
          <p class="font-medium">{{ peso(gig.my_bid.amount) }} · {{ gig.my_bid.delivery_days }} days</p>
          <p class="whitespace-pre-line text-muted-foreground">{{ gig.my_bid.proposal }}</p>
          <div v-if="gig.my_bid.status === 'pending'" class="flex gap-2 pt-2">
            <Button size="sm" variant="outline" @click="startEdit">Edit</Button>
            <Button size="sm" variant="destructive" @click="withdraw">Withdraw</Button>
          </div>
        </CardContent>
      </Card>

      <Card v-else-if="gig.status === 'approved'">
        <CardHeader><CardTitle class="text-lg">{{ editing ? 'Edit your bid' : 'Place a bid' }}</CardTitle></CardHeader>
        <CardContent>
          <form class="space-y-3" @submit.prevent="submitBid">
            <div class="space-y-1.5">
              <Label for="amount">Your price (PHP)</Label>
              <Input id="amount" v-model="bidForm.amount" type="number" min="50" max="100000" step="0.01" required />
            </div>
            <div class="space-y-1.5">
              <Label for="days">Delivery time (days)</Label>
              <Input id="days" v-model="bidForm.delivery_days" type="number" min="1" max="90" required />
            </div>
            <div class="space-y-1.5">
              <Label for="proposal">Proposal</Label>
              <Textarea id="proposal" v-model="bidForm.proposal" rows="5" minlength="20" maxlength="2000" required
                placeholder="Why are you a good fit? What will you deliver?" />
            </div>
            <Recaptcha v-if="!editing" ref="captchaRef" @verified="captcha = $event" @expired="captcha = null" />
            <div class="flex gap-2">
              <Button type="submit" :disabled="busy || (!editing && !captcha)">{{ editing ? 'Save bid' : 'Submit bid' }}</Button>
              <Button v-if="editing" type="button" variant="outline" @click="editing = false">Cancel</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

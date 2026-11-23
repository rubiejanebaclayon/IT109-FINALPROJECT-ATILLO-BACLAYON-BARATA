<script setup lang="ts">
definePageMeta({ middleware: 'auth', roles: ['freelancer'] })
const { api } = useApi()
const { user } = useAuth()
const { data: s } = await useAsyncData('dash-freelancer', () => api<any>('/dashboard/freelancer'))
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Welcome, {{ user?.full_name }}</h1>
        <p class="text-sm text-muted-foreground">Freelancer dashboard</p>
      </div>
      <Button as-child><NuxtLink to="/gigs">Find gigs</NuxtLink></Button>
    </div>

    <div v-if="s" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <StatCard label="Pending bids" :value="s.bids_pending" to="/my/bids" />
      <StatCard label="Accepted bids" :value="s.bids_accepted" to="/my/bids" />
      <StatCard label="Active contracts" :value="s.contracts_active" to="/contracts" />
      <StatCard label="Waiting for client payment" :value="s.contracts_awaiting_payment" to="/contracts" />
      <StatCard label="Paid out so far" :value="peso(s.earned)" to="/payouts" />
      <StatCard label="Payout pending" :value="peso(s.pending_payout)" to="/payouts" />
      <StatCard label="Portfolio items" :value="s.portfolio_items" to="/profile" hint="Show your best work" />
    </div>
  </div>
</template>

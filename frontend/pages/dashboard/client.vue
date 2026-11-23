<script setup lang="ts">
definePageMeta({ middleware: 'auth', roles: ['client'] })
const { api } = useApi()
const { user } = useAuth()
const { data: s } = await useAsyncData('dash-client', () => api<any>('/dashboard/client'))
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Welcome, {{ user?.full_name }}</h1>
        <p class="text-sm text-muted-foreground">Client dashboard</p>
      </div>
      <Button as-child><NuxtLink to="/gigs/new">+ Post a gig</NuxtLink></Button>
    </div>

    <div v-if="s" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <StatCard label="Gigs awaiting approval" :value="s.gigs_pending" to="/my/gigs" />
      <StatCard label="Open gigs" :value="s.gigs_open" to="/my/gigs" />
      <StatCard label="New bids to review" :value="s.bids_received" to="/my/gigs" hint="Open a gig to compare bids" />
      <StatCard label="Contracts awaiting payment" :value="s.contracts_awaiting_payment" to="/contracts" />
      <StatCard label="Active contracts" :value="s.contracts_active" to="/contracts" />
      <StatCard label="Work waiting for your approval" :value="s.contracts_to_approve" to="/contracts" />
    </div>
  </div>
</template>

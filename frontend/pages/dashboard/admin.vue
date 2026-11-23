<script setup lang="ts">
definePageMeta({ middleware: 'auth', roles: ['admin'] })
const { api } = useApi()
const { data: s } = await useAsyncData('dash-admin', () => api<any>('/dashboard/admin'))
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold">Admin dashboard</h1>
      <p class="text-sm text-muted-foreground">Moderation, escrow and manual payouts</p>
    </div>

    <div v-if="s" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard label="Users" :value="s.users" to="/admin/users" />
      <StatCard label="Gigs to review" :value="s.gigs_pending_review" to="/admin/gigs" />
      <StatCard label="Approved gigs" :value="s.gigs_approved" />
      <StatCard label="Funded contracts" :value="s.contracts_funded" to="/contracts" />
      <StatCard label="Held in escrow" :value="peso(s.escrow_held)" />
      <StatCard label="Payouts to send" :value="s.payouts_pending" to="/admin/payouts" />
      <StatCard label="Payouts completed" :value="s.payouts_paid" to="/admin/payouts" />
    </div>
  </div>
</template>

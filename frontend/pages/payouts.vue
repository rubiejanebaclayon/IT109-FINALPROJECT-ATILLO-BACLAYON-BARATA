<script setup lang="ts">
definePageMeta({ middleware: 'auth', roles: ['freelancer'] })
const { api } = useApi()
const { data: payouts, pending } = await useAsyncData('my-payouts', () => api<any[]>('/payouts/mine'))
</script>

<template>
  <div class="space-y-5">
    <div>
      <h1 class="text-2xl font-bold">My payouts</h1>
      <p class="text-sm text-muted-foreground">Payouts are sent and recorded manually by the administrator after the client approves your work.</p>
    </div>
    <p v-if="pending && !payouts" class="text-muted-foreground">Loading…</p>
    <p v-else-if="!payouts?.length" class="rounded-xl border bg-background p-8 text-center text-muted-foreground">No payouts yet.</p>
    <div v-else class="overflow-x-auto rounded-xl border bg-background">
      <table class="w-full text-left text-sm">
        <thead class="border-b bg-muted/50 text-xs uppercase text-muted-foreground">
          <tr><th class="p-3">Gig</th><th class="p-3">Gross</th><th class="p-3">Fee</th><th class="p-3">Net</th><th class="p-3">Status</th><th class="p-3">Method / ref</th><th class="p-3">Paid</th></tr>
        </thead>
        <tbody>
          <tr v-for="p in payouts" :key="p.id" class="border-b last:border-0">
            <td class="p-3 font-medium"><NuxtLink :to="`/contracts/${p.contract_id}`" class="hover:underline">{{ p.gig_title }}</NuxtLink></td>
            <td class="p-3">{{ peso(p.gross_amount) }}</td>
            <td class="p-3">{{ peso(p.platform_fee) }}</td>
            <td class="p-3 font-medium">{{ peso(p.net_amount) }}</td>
            <td class="p-3"><StatusBadge :status="p.status" /></td>
            <td class="p-3">{{ p.method ? `${p.method} · ${p.reference_no}` : '-' }}</td>
            <td class="p-3">{{ fdate(p.paid_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
const { api } = useApi()
const { user } = useAuth()
const { data: contracts, pending } = await useAsyncData('contracts', () => api<any[]>('/contracts'))
</script>

<template>
  <div class="space-y-5">
    <h1 class="text-2xl font-bold">{{ user?.role === 'admin' ? 'All contracts' : 'My contracts' }}</h1>
    <p v-if="pending && !contracts" class="text-muted-foreground">Loading…</p>
    <p v-else-if="!contracts?.length" class="rounded-xl border bg-background p-8 text-center text-muted-foreground">
      No contracts yet. A contract is created when a client selects a freelancer's bid.
    </p>
    <div v-else class="overflow-x-auto rounded-xl border bg-background">
      <table class="w-full text-left text-sm">
        <thead class="border-b bg-muted/50 text-xs uppercase text-muted-foreground">
          <tr><th class="p-3">Gig</th><th class="p-3">Client</th><th class="p-3">Freelancer</th><th class="p-3">Amount</th><th class="p-3">Status</th><th class="p-3">Created</th></tr>
        </thead>
        <tbody>
          <tr v-for="c in contracts" :key="c.id" class="border-b last:border-0">
            <td class="p-3 font-medium"><NuxtLink :to="`/contracts/${c.id}`" class="hover:underline">{{ c.gig_title }}</NuxtLink></td>
            <td class="p-3">{{ c.client_name }}</td>
            <td class="p-3">{{ c.freelancer_name }}</td>
            <td class="p-3">{{ peso(c.amount) }}</td>
            <td class="p-3"><StatusBadge :status="c.status" /></td>
            <td class="p-3">{{ fdate(c.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

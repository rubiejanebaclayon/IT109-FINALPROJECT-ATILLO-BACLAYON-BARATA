<script setup lang="ts">
definePageMeta({ middleware: 'auth', roles: ['freelancer'] })
const { api } = useApi()
const { data: bids, pending } = await useAsyncData('my-bids', () => api<any[]>('/bids/mine'))
</script>

<template>
  <div class="space-y-5">
    <h1 class="text-2xl font-bold">My bids</h1>
    <p v-if="pending && !bids" class="text-muted-foreground">Loading…</p>
    <p v-else-if="!bids?.length" class="rounded-xl border bg-background p-8 text-center text-muted-foreground">
      You have not placed any bids. <NuxtLink to="/gigs" class="underline">Browse gigs</NuxtLink>
    </p>
    <div v-else class="overflow-x-auto rounded-xl border bg-background">
      <table class="w-full text-left text-sm">
        <thead class="border-b bg-muted/50 text-xs uppercase text-muted-foreground">
          <tr><th class="p-3">Gig</th><th class="p-3">My price</th><th class="p-3">Days</th><th class="p-3">Bid</th><th class="p-3"></th></tr>
        </thead>
        <tbody>
          <tr v-for="b in bids" :key="b.id" class="border-b last:border-0">
            <td class="p-3 font-medium"><NuxtLink :to="`/gigs/${b.gig_id}`" class="hover:underline">{{ b.gig_title }}</NuxtLink></td>
            <td class="p-3">{{ peso(b.amount) }}</td>
            <td class="p-3">{{ b.delivery_days }}</td>
            <td class="p-3"><StatusBadge :status="b.status" /></td>
            <td class="p-3">
              <NuxtLink v-if="b.contract_id" :to="`/contracts/${b.contract_id}`" class="text-primary underline">Open contract</NuxtLink>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

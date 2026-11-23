<script setup lang="ts">
definePageMeta({ middleware: 'auth', roles: ['client'] })
const { api } = useApi()
const route = useRoute()
const { data: gigs, pending } = await useAsyncData('my-gigs', () => api<any[]>('/gigs/mine'))
</script>

<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">My gigs</h1>
      <Button as-child><NuxtLink to="/gigs/new">+ Post a gig</NuxtLink></Button>
    </div>
    <p v-if="route.query.created" class="rounded-md bg-emerald-50 p-2 text-sm text-emerald-700">
      Gig submitted. It will appear publicly once an administrator approves it.
    </p>
    <p v-if="route.query.updated" class="rounded-md bg-emerald-50 p-2 text-sm text-emerald-700">
      Gig updated and sent for approval again.
    </p>

    <p v-if="pending && !gigs" class="text-muted-foreground">Loading…</p>
    <p v-else-if="!gigs?.length" class="rounded-xl border bg-background p-8 text-center text-muted-foreground">
      You have not posted any gigs yet.
    </p>

    <div v-else class="overflow-x-auto rounded-xl border bg-background">
      <table class="w-full text-left text-sm">
        <thead class="border-b bg-muted/50 text-xs uppercase text-muted-foreground">
          <tr><th class="p-3">Title</th><th class="p-3">Budget</th><th class="p-3">Deadline</th><th class="p-3">Bids</th><th class="p-3">Status</th></tr>
        </thead>
        <tbody>
          <tr v-for="g in gigs" :key="g.id" class="border-b last:border-0">
            <td class="p-3 font-medium"><NuxtLink :to="`/gigs/${g.id}`" class="hover:underline">{{ g.title }}</NuxtLink></td>
            <td class="p-3">{{ peso(g.budget_min) }} – {{ peso(g.budget_max) }}</td>
            <td class="p-3">{{ fdate(g.deadline) }}</td>
            <td class="p-3">{{ g.bid_count }}</td>
            <td class="p-3"><StatusBadge :status="g.status" /></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

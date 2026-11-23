<script setup lang="ts">
const { user } = useAuth()
const steps = [
  ['1. Post', 'Clients describe the gig and set a budget.'],
  ['2. Bid', 'Student freelancers send proposals.'],
  ['3. Fund', 'The client prepays; money is held in escrow.'],
  ['4. Deliver', 'The freelancer shares the work by link (e.g. Google Drive).'],
  ['5. Approve & payout', 'The client approves; the admin records the payout.'],
]
</script>

<template>
  <section class="rounded-2xl border bg-background px-6 py-12 text-center shadow-sm">
    <h1 class="text-3xl font-bold tracking-tight sm:text-4xl">Student services, safely paid.</h1>
    <p class="mx-auto mt-3 max-w-xl text-muted-foreground">
      Find student freelancers for graphic design, proofreading, tutoring and more, or offer your own skills.
    </p>
    <div class="mt-6 flex justify-center gap-3">
      <Button as-child><NuxtLink to="/gigs">Browse gigs</NuxtLink></Button>
      <Button v-if="!user" variant="outline" as-child><NuxtLink to="/login">Log in with Google</NuxtLink></Button>
      <Button v-else variant="outline" as-child><NuxtLink to="/dashboard">Go to dashboard</NuxtLink></Button>
    </div>
  </section>

  <section class="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
    <Card v-for="s in steps" :key="s[0]">
      <CardHeader class="pb-2"><CardTitle class="text-base">{{ s[0] }}</CardTitle></CardHeader>
      <CardContent class="text-sm text-muted-foreground">{{ s[1] }}</CardContent>
    </Card>
  </section>
</template> 
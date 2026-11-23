<script setup lang="ts">
// Public listing of APPROVED gigs (the backend serves it from cache).
const { api } = useApi()
const categories = await api<string[]>('/gigs/categories').catch(() => [])

const filters = reactive({ q: '', category: '', sort: 'newest', page: 1 })
const pageSize = 12

const { data, pending, error, refresh } = await useAsyncData(
  'gig-list',
  () => api<any>('/gigs', {
    query: { q: filters.q || undefined, category: filters.category || undefined, sort: filters.sort,
             page: filters.page, page_size: pageSize },
  }),
  { watch: [() => filters.category, () => filters.sort, () => filters.page] },
)
const totalPages = computed(() => Math.max(1, Math.ceil((data.value?.total || 0) / pageSize)))

function search() {
  filters.page = 1
  refresh()
}
</script>

<template>
  <div class="space-y-5">
    <h1 class="text-2xl font-bold">Browse gigs</h1>

    <form class="grid gap-3 rounded-xl border bg-background p-4 sm:grid-cols-4" @submit.prevent="search">
      <Input v-model="filters.q" placeholder="Search title or description" maxlength="80" class="sm:col-span-2" />
      <AppSelect v-model="filters.category">
        <option value="">All categories</option>
        <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
      </AppSelect>
      <AppSelect v-model="filters.sort">
        <option value="newest">Newest</option>
        <option value="deadline">Deadline soonest</option>
        <option value="budget_high">Highest budget</option>
      </AppSelect>
    </form>

    <p v-if="error" class="text-sm text-destructive">{{ error.message }}</p>
    <p v-else-if="pending && !data" class="text-muted-foreground">Loading…</p>
    <p v-else-if="!data?.items.length" class="rounded-xl border bg-background p-8 text-center text-muted-foreground">
      No gigs found.
    </p>

    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <NuxtLink v-for="g in data.items" :key="g.id" :to="`/gigs/${g.id}`">
        <Card class="h-full transition hover:border-primary">
          <CardHeader class="pb-2">
            <Badge variant="secondary" class="w-fit">{{ g.category }}</Badge>
            <CardTitle class="text-base leading-snug">{{ g.title }}</CardTitle>
            <CardDescription>by {{ g.client_name }}</CardDescription>
          </CardHeader>
          <CardContent class="space-y-2 text-sm">
            <p class="line-clamp-3 text-muted-foreground">{{ g.summary }}</p>
            <p class="font-medium">{{ peso(g.budget_min) }} – {{ peso(g.budget_max) }}</p>
            <p class="text-xs text-muted-foreground">Due {{ fdate(g.deadline) }} · {{ g.bid_count }} bid{{ g.bid_count === 1 ? '' : 's' }}</p>
          </CardContent>
        </Card>
      </NuxtLink>
    </div>

    <div v-if="totalPages > 1" class="flex items-center justify-center gap-3">
      <Button variant="outline" size="sm" :disabled="filters.page <= 1" @click="filters.page--">Previous</Button>
      <span class="text-sm">Page {{ filters.page }} of {{ totalPages }}</span>
      <Button variant="outline" size="sm" :disabled="filters.page >= totalPages" @click="filters.page++">Next</Button>
    </div>
  </div>
</template>

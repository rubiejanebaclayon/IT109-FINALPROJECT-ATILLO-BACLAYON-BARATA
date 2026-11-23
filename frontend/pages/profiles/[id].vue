<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
const route = useRoute()
const { api } = useApi()
const { data: p, error } = await useAsyncData(`profile-${route.params.id}`, () => api<any>(`/profiles/${route.params.id}`))
</script>

<template>
  <p v-if="error || !p" class="py-10 text-center text-muted-foreground">Profile not found.</p>
  <div v-else class="mx-auto max-w-3xl space-y-6">
    <Card>
      <CardContent class="flex items-start gap-4 pt-6">
        <img v-if="p.avatar_url" :src="p.avatar_url" alt="" referrerpolicy="no-referrer" class="h-16 w-16 rounded-full" />
        <div v-else class="flex h-16 w-16 items-center justify-center rounded-full bg-muted text-lg font-semibold">{{ initials(p.full_name) }}</div>
        <div class="space-y-1">
          <h1 class="text-xl font-bold">{{ p.full_name }}</h1>
          <p v-if="p.headline" class="text-sm text-muted-foreground">{{ p.headline }}</p>
          <p v-if="p.school_or_dept || p.city_name" class="text-xs text-muted-foreground">
            {{ [p.school_or_dept, p.city_name, p.province_name].filter(Boolean).join(' · ') }}
          </p>
          <p v-if="p.bio" class="whitespace-pre-line pt-2 text-sm">{{ p.bio }}</p>
          <div v-if="p.skills?.length" class="flex flex-wrap gap-1 pt-2">
            <Badge v-for="s in p.skills" :key="s" variant="outline">{{ s }}</Badge>
          </div>
        </div>
      </CardContent>
    </Card>

    <Card v-if="p.role === 'freelancer'">
      <CardHeader><CardTitle class="text-lg">Portfolio</CardTitle></CardHeader>
      <CardContent>
        <p v-if="!p.portfolio.length" class="text-sm text-muted-foreground">No portfolio items yet.</p>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="it in p.portfolio" :key="it.id" class="overflow-hidden rounded-lg border">
            <img v-if="it.content_type.startsWith('image/')" :src="it.asset_url" :alt="it.title" class="h-36 w-full object-cover" />
            <a v-else :href="it.asset_url" target="_blank" rel="noopener noreferrer"
              class="flex h-36 items-center justify-center bg-muted text-sm underline">Open PDF</a>
            <div class="p-3 text-sm">
              <p class="font-medium">{{ it.title }}</p>
              <p v-if="it.description" class="text-xs text-muted-foreground">{{ it.description }}</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

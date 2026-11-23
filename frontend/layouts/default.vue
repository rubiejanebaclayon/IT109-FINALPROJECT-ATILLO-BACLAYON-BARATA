<script setup lang="ts">
const { user, ensureUser, logout } = useAuth()
await ensureUser()

const links = computed(() => {
  const base = [{ to: '/gigs', label: 'Browse gigs' }]
  switch (user.value?.role) {
    case 'client':
      return [...base, { to: '/dashboard', label: 'Dashboard' }, { to: '/gigs/new', label: 'Post a gig' },
        { to: '/my/gigs', label: 'My gigs' }, { to: '/contracts', label: 'Contracts' }]
    case 'freelancer':
      return [...base, { to: '/dashboard', label: 'Dashboard' }, { to: '/my/bids', label: 'My bids' },
        { to: '/contracts', label: 'Contracts' }, { to: '/payouts', label: 'Payouts' }]
    case 'admin':
      return [...base, { to: '/dashboard', label: 'Dashboard' }, { to: '/admin/gigs', label: 'Gig approvals' },
        { to: '/contracts', label: 'Contracts' }, { to: '/admin/payouts', label: 'Payouts' },
        { to: '/admin/users', label: 'Users' }]
    default:
      return base
  }
})
const open = ref(false)
const route = useRoute()
watch(() => route.fullPath, () => (open.value = false))
</script>

<template>
  <div class="min-h-screen bg-muted/30 text-foreground">
    <header class="sticky top-0 z-20 border-b bg-background">
      <div class="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <NuxtLink to="/" class="font-semibold tracking-tight">🎓 Student Gig Marketplace</NuxtLink>

        <nav class="hidden items-center gap-1 md:flex">
          <NuxtLink v-for="l in links" :key="l.to" :to="l.to"
            class="rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
            active-class="bg-muted text-foreground">{{ l.label }}</NuxtLink>
        </nav>

        <div class="hidden items-center gap-2 md:flex">
          <template v-if="user">
            <NuxtLink to="/profile" class="flex items-center gap-2 text-sm hover:underline">
              <img v-if="user.avatar_url" :src="user.avatar_url" alt="" referrerpolicy="no-referrer"
                class="h-7 w-7 rounded-full" />
              <span>{{ user.full_name }}</span>
            </NuxtLink>
            <Badge variant="secondary" class="capitalize">{{ user.role }}</Badge>
            <Button variant="outline" size="sm" @click="logout">Log out</Button>
          </template>
          <Button v-else size="sm" as-child><NuxtLink to="/login">Log in</NuxtLink></Button>
        </div>

        <button class="rounded-md border px-2 py-1 text-sm md:hidden" aria-label="Menu" @click="open = !open">☰</button>
      </div>

      <div v-if="open" class="border-t px-4 py-3 md:hidden">
        <NuxtLink v-for="l in links" :key="l.to" :to="l.to" class="block py-2 text-sm">{{ l.label }}</NuxtLink>
        <NuxtLink v-if="user" to="/profile" class="block py-2 text-sm">My profile</NuxtLink>
        <button v-if="user" class="py-2 text-sm text-destructive" @click="logout">Log out</button>
        <NuxtLink v-else to="/login" class="block py-2 text-sm">Log in</NuxtLink>
      </div>
    </header>

    <main class="mx-auto max-w-6xl px-4 py-6">
      <slot />
    </main>

    <footer class="border-t py-6 text-center text-xs text-muted-foreground">
      IT 109 – System Integration and Architecture · Sandbox payments only (PayMongo test mode)
    </footer>
  </div>
</template>

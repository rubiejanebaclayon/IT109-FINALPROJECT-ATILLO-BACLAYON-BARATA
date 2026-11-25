<script setup lang="ts">
const { user, ensureUser, logout } = useAuth()
await ensureUser()

const links = computed(() => {
  const base = [{ to: '/gigs', label: 'Browse gigs', icon: '⌕' }]
  switch (user.value?.role) {
    case 'client':
      return [...base, { to: '/dashboard', label: 'Dashboard', icon: '▦' }, { to: '/gigs/new', label: 'Post a gig', icon: '+' },
        { to: '/my/gigs', label: 'My gigs', icon: '▤' }, { to: '/contracts', label: 'Contracts', icon: '◇' }]
    case 'freelancer':
      return [...base, { to: '/dashboard', label: 'Dashboard', icon: '▦' }, { to: '/my/bids', label: 'My bids', icon: '↗' },
        { to: '/contracts', label: 'Contracts', icon: '◇' }, { to: '/payouts', label: 'Payouts', icon: '₱' }]
    case 'admin':
      return [...base, { to: '/dashboard', label: 'Dashboard', icon: '▦' }, { to: '/admin/gigs', label: 'Gig approvals', icon: '✓' },
        { to: '/contracts', label: 'Contracts', icon: '◇' }, { to: '/admin/payouts', label: 'Payouts', icon: '₱' },
        { to: '/admin/users', label: 'Users', icon: '♙' }]
    default:
      return base
  }
})
const open = ref(false)
const route = useRoute()
watch(() => route.fullPath, () => (open.value = false))
</script>

<template>
  <div class="market-shell min-h-screen">
    <aside class="market-sidebar">
      <NuxtLink to="/" class="brand-lockup">
        <span class="brand-mark">SG</span>
        <span class="brand-copy"><strong>Student Gig</strong><small>& Skill Marketplace</small></span>
      </NuxtLink>

      <div class="sidebar-caption">WORKSPACE</div>
      <nav class="sidebar-nav" aria-label="Main navigation">
        <NuxtLink v-for="l in links" :key="l.to" :to="l.to" class="sidebar-link" active-class="is-active">
          <span class="sidebar-icon" aria-hidden="true">{{ l.icon }}</span>
          <span>{{ l.label }}</span>
          <span v-if="l.to === '/admin/gigs' && user?.role === 'admin'" class="nav-dot" />
        </NuxtLink>
      </nav>

      <div class="sidebar-bottom">
        <div class="sidebar-caption">ACCOUNT</div>
        <NuxtLink v-if="user" to="/profile" class="account-link">
          <img v-if="user.avatar_url" :src="user.avatar_url" alt="" referrerpolicy="no-referrer" class="account-avatar" />
          <span v-else class="account-avatar account-avatar-fallback">{{ user.full_name?.charAt(0)?.toUpperCase() || 'U' }}</span>
          <span class="account-copy"><strong>{{ user.full_name }}</strong><small class="capitalize">{{ user.role }}</small></span>
        </NuxtLink>
        <NuxtLink v-else to="/login" class="sidebar-link">Log in / Sign up</NuxtLink>
        <button v-if="user" class="sidebar-logout" @click="logout">↪ <span>Log out</span></button>
      </div>
      <div class="sidebar-footer">IT 109 · Student Marketplace</div>
    </aside>

    <div class="market-main">
      <header class="market-topbar">
        <button class="mobile-menu-button" aria-label="Toggle navigation" @click="open = !open">☰</button>
        <div class="topbar-breadcrumb"><span>Workspace</span><span class="breadcrumb-slash">/</span><strong>{{ route.meta.title || (route.path.split('/').filter(Boolean).pop()?.replace(/-/g, ' ') || 'Home') }}</strong></div>
        <div class="topbar-right">
          <span class="topbar-status"><i /> Student platform</span>
          <NuxtLink v-if="user" to="/profile" class="topbar-profile">My profile</NuxtLink>
          <NuxtLink v-else to="/login" class="topbar-profile">Sign in</NuxtLink>
        </div>
      </header>

      <div v-if="open" class="mobile-nav-panel">
        <NuxtLink v-for="l in links" :key="l.to" :to="l.to" class="mobile-nav-link">{{ l.label }}</NuxtLink>
        <NuxtLink v-if="user" to="/profile" class="mobile-nav-link">My profile</NuxtLink>
        <button v-if="user" class="mobile-nav-link" @click="logout">Log out</button>
        <NuxtLink v-else to="/login" class="mobile-nav-link">Log in</NuxtLink>
      </div>

      <main class="market-content">
        <slot />
      </main>
      <footer class="market-footer">Student Gig & Skill Marketplace <span>·</span> IT 109 – System Integration and Architecture <span>·</span> Sandbox payments only</footer>
    </div>
  </div>
</template>

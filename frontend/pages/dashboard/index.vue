<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
const { user } = useAuth()
// Send each role to its own dashboard
await navigateTo(`/dashboard/${user.value?.role}`, { replace: true })
</script>

<template><p class="py-20 text-center text-muted-foreground">Loading…</p></template>

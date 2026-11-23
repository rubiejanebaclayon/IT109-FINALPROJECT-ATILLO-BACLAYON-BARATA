<script setup lang="ts">
defineProps<{ label: string; value: string | number; to?: string; hint?: string }>()
const NuxtLink = resolveComponent('NuxtLink')
</script>

<template>
  <component :is="to ? NuxtLink : 'div'" :to="to"
    class="block rounded-xl border bg-card p-4 shadow-sm transition" :class="to ? 'hover:border-primary' : ''">
    <p class="text-xs uppercase tracking-wide text-muted-foreground">{{ label }}</p>
    <p class="mt-1 text-2xl font-semibold">{{ value }}</p>
    <p v-if="hint" class="mt-1 text-xs text-muted-foreground">{{ hint }}</p>
  </component>
</template>

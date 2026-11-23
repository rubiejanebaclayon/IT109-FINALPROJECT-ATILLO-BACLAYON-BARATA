<script setup lang="ts">
// Native <select> styled to match the shadcn inputs (simple and accessible).
const model = defineModel<string | null | undefined>()
</script>

<template>
  <select v-model="model"
    class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50">
    <slot />
  </select>
</template>

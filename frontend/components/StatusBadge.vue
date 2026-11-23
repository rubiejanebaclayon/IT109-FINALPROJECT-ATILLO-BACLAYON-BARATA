<script setup lang="ts">
const props = defineProps<{ status: string }>()

const styles: Record<string, string> = {
  pending_approval: 'bg-amber-100 text-amber-800',
  approved: 'bg-emerald-100 text-emerald-800',
  rejected: 'bg-red-100 text-red-800',
  awarded: 'bg-indigo-100 text-indigo-800',
  closed: 'bg-slate-200 text-slate-700',
  cancelled: 'bg-slate-200 text-slate-700',
  pending: 'bg-amber-100 text-amber-800',
  accepted: 'bg-emerald-100 text-emerald-800',
  withdrawn: 'bg-slate-200 text-slate-700',
  pending_payment: 'bg-amber-100 text-amber-800',
  funded: 'bg-sky-100 text-sky-800',
  submitted: 'bg-violet-100 text-violet-800',
  paid_out: 'bg-emerald-100 text-emerald-800',
  paid: 'bg-emerald-100 text-emerald-800',
  processing: 'bg-sky-100 text-sky-800',
  failed: 'bg-red-100 text-red-800',
}
const cls = computed(() => styles[props.status] || 'bg-slate-100 text-slate-700')
const label = computed(() => props.status.replace(/_/g, ' '))
</script>

<template>
  <span class="inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize" :class="cls">{{ label }}</span>
</template>

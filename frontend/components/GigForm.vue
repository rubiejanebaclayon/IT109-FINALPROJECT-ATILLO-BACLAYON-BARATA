<script setup lang="ts">
// Used by "Post a gig" and "Edit gig". Includes reCAPTCHA only when creating.
const props = defineProps<{ initial?: any; submitLabel: string; useCaptcha?: boolean; busy?: boolean }>()
const emit = defineEmits<{ (e: 'submit', payload: { body: any; captcha: string | null }): void }>()
const { api } = useApi()

const categories = await api<string[]>('/gigs/categories').catch(() => [])
const form = reactive({
  title: props.initial?.title ?? '',
  description: props.initial?.description ?? '',
  category: props.initial?.category ?? '',
  budget_min: props.initial?.budget_min ?? 100,
  budget_max: props.initial?.budget_max ?? 500,
  deadline: props.initial?.deadline ?? '',
})
const captcha = ref<string | null>(null)
const captchaRef = ref<{ reset: () => void } | null>(null)
const minDate = new Date(Date.now() + 86400000).toISOString().slice(0, 10)

function submit() {
  emit('submit', {
    body: { ...form, budget_min: Number(form.budget_min), budget_max: Number(form.budget_max) },
    captcha: captcha.value,
  })
  captchaRef.value?.reset()
}
defineExpose({ resetCaptcha: () => captchaRef.value?.reset() })
</script>

<template>
  <form class="space-y-4" @submit.prevent="submit">
    <div class="space-y-1.5">
      <Label for="title">Title</Label>
      <Input id="title" v-model="form.title" required minlength="5" maxlength="150" placeholder="e.g. Poster design for org event" />
    </div>
    <div class="space-y-1.5">
      <Label for="desc">Description</Label>
      <Textarea id="desc" v-model="form.description" required minlength="20" maxlength="4000" rows="6"
        placeholder="Describe the work, format, and anything the freelancer should know." />
    </div>
    <div class="grid gap-4 sm:grid-cols-2">
      <div class="space-y-1.5">
        <Label for="cat">Category</Label>
        <AppSelect id="cat" v-model="form.category" required>
          <option value="" disabled>Select a category</option>
          <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
        </AppSelect>
      </div>
      <div class="space-y-1.5">
        <Label for="deadline">Deadline</Label>
        <Input id="deadline" v-model="form.deadline" type="date" :min="minDate" required />
      </div>
      <div class="space-y-1.5">
        <Label for="bmin">Minimum budget (PHP)</Label>
        <Input id="bmin" v-model="form.budget_min" type="number" min="50" max="100000" step="0.01" required />
      </div>
      <div class="space-y-1.5">
        <Label for="bmax">Maximum budget (PHP)</Label>
        <Input id="bmax" v-model="form.budget_max" type="number" min="50" max="100000" step="0.01" required />
      </div>
    </div>
    <Recaptcha v-if="useCaptcha" ref="captchaRef" @verified="captcha = $event" @expired="captcha = null" />
    <Button type="submit" :disabled="busy || (useCaptcha && !captcha)">{{ busy ? 'Saving…' : submitLabel }}</Button>
  </form>
</template>

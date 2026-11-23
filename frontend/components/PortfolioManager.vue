<script setup lang="ts">
// Freelancer portfolio: upload (to Supabase Storage via the backend), rename, delete.
const props = defineProps<{ items: any[] }>()
const emit = defineEmits<{ (e: 'changed'): void }>()
const { api } = useApi()

const title = ref('')
const description = ref('')
const file = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const busy = ref(false)
const error = ref('')

const MAX = 5 * 1024 * 1024
function pick(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0] || null
  error.value = ''
  if (f && f.size > MAX) {
    error.value = 'File is too large (max 5 MB).'
    file.value = null
    if (fileInput.value) fileInput.value.value = ''
    return
  }
  file.value = f
}

async function upload() {
  if (!file.value) return
  busy.value = true
  error.value = ''
  try {
    const fd = new FormData()
    fd.append('title', title.value)
    if (description.value) fd.append('description', description.value)
    fd.append('file', file.value)
    await api('/portfolio', { method: 'POST', body: fd })
    title.value = description.value = ''
    file.value = null
    if (fileInput.value) fileInput.value.value = ''
    emit('changed')
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function rename(item: any) {
  const t = window.prompt('New title', item.title)
  if (!t || t === item.title) return
  try {
    await api(`/portfolio/${item.id}`, { method: 'PUT', body: { title: t, description: item.description } })
    emit('changed')
  } catch (e: any) {
    error.value = e.message
  }
}

async function remove(item: any) {
  if (!confirm(`Delete "${item.title}"?`)) return
  try {
    await api(`/portfolio/${item.id}`, { method: 'DELETE' })
    emit('changed')
  } catch (e: any) {
    error.value = e.message
  }
}
</script>

<template>
  <div class="space-y-4">
    <p v-if="error" class="rounded-md bg-red-50 p-2 text-sm text-red-700">{{ error }}</p>

    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="it in props.items" :key="it.id" class="overflow-hidden rounded-lg border bg-background">
        <img v-if="it.content_type.startsWith('image/')" :src="it.asset_url" :alt="it.title" class="h-36 w-full object-cover" />
        <a v-else :href="it.asset_url" target="_blank" rel="noopener noreferrer"
          class="flex h-36 items-center justify-center bg-muted text-sm underline">Open PDF</a>
        <div class="space-y-1 p-3 text-sm">
          <p class="font-medium">{{ it.title }}</p>
          <p v-if="it.description" class="text-xs text-muted-foreground">{{ it.description }}</p>
          <div class="flex gap-2 pt-1">
            <Button size="sm" variant="outline" @click="rename(it)">Rename</Button>
            <Button size="sm" variant="destructive" @click="remove(it)">Delete</Button>
          </div>
        </div>
      </div>
    </div>
    <p v-if="!props.items.length" class="text-sm text-muted-foreground">No portfolio items yet.</p>

    <form class="space-y-3 rounded-lg border p-4" @submit.prevent="upload">
      <p class="text-sm font-medium">Add a portfolio item</p>
      <div class="grid gap-3 sm:grid-cols-2">
        <div class="space-y-1.5">
          <Label for="pt">Title</Label>
          <Input id="pt" v-model="title" required minlength="3" maxlength="120" />
        </div>
        <div class="space-y-1.5">
          <Label for="pf">File (PNG, JPG, WEBP or PDF, max 5 MB)</Label>
          <input id="pf" ref="fileInput" type="file" required accept="image/png,image/jpeg,image/webp,application/pdf"
            class="block w-full text-sm" @change="pick" />
        </div>
      </div>
      <div class="space-y-1.5">
        <Label for="pd">Description (optional)</Label>
        <Textarea id="pd" v-model="description" rows="2" maxlength="1000" />
      </div>
      <Button type="submit" :disabled="busy || !file">{{ busy ? 'Uploading…' : 'Upload' }}</Button>
    </form>
  </div>
</template>

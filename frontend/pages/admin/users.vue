<script setup lang="ts">
definePageMeta({ middleware: 'auth', roles: ['admin'] })
const { api } = useApi()
const { user: me } = useAuth()
const role = ref('')
const { data: users, pending, refresh } = await useAsyncData('admin-users',
  () => api<any[]>('/admin/users', { query: { role: role.value || undefined } }), { watch: [role] })
const error = ref('')

async function patch(u: any, body: any) {
  error.value = ''
  try {
    await api(`/admin/users/${u.id}`, { method: 'PATCH', body })
    await refresh()
  } catch (e: any) { error.value = e.message }
}
const changeRole = (u: any, r: string) =>
  confirm(`Change ${u.full_name} to ${r}?`) ? patch(u, { role: r }) : refresh()
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-bold">Users</h1>
      <div class="w-48">
        <AppSelect v-model="role">
          <option value="">All roles</option>
          <option value="client">Clients</option>
          <option value="freelancer">Freelancers</option>
          <option value="admin">Admins</option>
        </AppSelect>
      </div>
    </div>
    <p v-if="error" class="rounded-md bg-red-50 p-2 text-sm text-red-700">{{ error }}</p>
    <p v-if="pending && !users" class="text-muted-foreground">Loading…</p>

    <div v-else class="overflow-x-auto rounded-xl border bg-background">
      <table class="w-full text-left text-sm">
        <thead class="border-b bg-muted/50 text-xs uppercase text-muted-foreground">
          <tr><th class="p-3">Name</th><th class="p-3">Email</th><th class="p-3">Role</th><th class="p-3">Joined</th><th class="p-3">Active</th></tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id" class="border-b last:border-0">
            <td class="p-3 font-medium">{{ u.full_name }}</td>
            <td class="p-3">{{ u.email }}</td>
            <td class="p-3">
              <select :value="u.role" :disabled="u.id === me?.id" class="rounded-md border bg-background px-2 py-1 text-sm"
                @change="changeRole(u, ($event.target as HTMLSelectElement).value)">
                <option value="client">client</option>
                <option value="freelancer">freelancer</option>
                <option value="admin">admin</option>
              </select>
            </td>
            <td class="p-3">{{ fdate(u.created_at) }}</td>
            <td class="p-3">
              <Button size="sm" :variant="u.is_active ? 'outline' : 'destructive'" :disabled="u.id === me?.id"
                @click="patch(u, { is_active: !u.is_active })">{{ u.is_active ? 'Disable' : 'Enable' }}</Button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
const { api } = useApi()
const { user } = useAuth()

const { data, refresh } = await useAsyncData('my-profile', () => api<any>('/profiles/me'))

type Opt = { code: string; name: string }
const form = reactive({
  full_name: data.value?.user.full_name || '',
  headline: data.value?.profile?.headline || '',
  bio: data.value?.profile?.bio || '',
  skillsText: (data.value?.profile?.skills || []).join(', '),
  school_or_dept: data.value?.profile?.school_or_dept || '',
  contact_number: data.value?.profile?.contact_number || '',
})
const addr = reactive({
  region_code: data.value?.profile?.region_code || '',
  province_code: data.value?.profile?.province_code || '',
  city_code: data.value?.profile?.city_code || '',
  barangay_code: data.value?.profile?.barangay_code || '',
})
const regions = ref<Opt[]>([])
const provinces = ref<Opt[]>([])
const cities = ref<Opt[]>([])
const barangays = ref<Opt[]>([])
const msg = ref('')
const error = ref('')
const saving = ref(false)

const get = (path: string) => api<Opt[]>(path).catch(() => [] as Opt[])

// Cascading PSGC dropdowns. NCR has no provinces, so we fall back to its cities.
async function onRegion() {
  Object.assign(addr, { province_code: '', city_code: '', barangay_code: '' })
  provinces.value = cities.value = barangays.value = []
  if (!addr.region_code) return
  provinces.value = await get(`/psgc/regions/${addr.region_code}/provinces`)
  if (!provinces.value.length) cities.value = await get(`/psgc/regions/${addr.region_code}/cities`)
}
async function onProvince() {
  Object.assign(addr, { city_code: '', barangay_code: '' })
  cities.value = barangays.value = []
  if (addr.province_code) cities.value = await get(`/psgc/provinces/${addr.province_code}/cities`)
}
async function onCity() {
  addr.barangay_code = ''
  barangays.value = []
  if (addr.city_code) barangays.value = await get(`/psgc/cities/${addr.city_code}/barangays`)
}

onMounted(async () => {
  regions.value = await get('/psgc/regions')
  // Preload saved selections without clearing them
  if (addr.region_code) {
    provinces.value = await get(`/psgc/regions/${addr.region_code}/provinces`)
    if (!provinces.value.length) cities.value = await get(`/psgc/regions/${addr.region_code}/cities`)
  }
  if (addr.province_code) cities.value = await get(`/psgc/provinces/${addr.province_code}/cities`)
  if (addr.city_code) barangays.value = await get(`/psgc/cities/${addr.city_code}/barangays`)
})

const nameOf = (list: Opt[], code: string) => list.find((o) => o.code === code)?.name || null

async function save() {
  saving.value = true
  error.value = msg.value = ''
  try {
    const body = {
      full_name: form.full_name,
      headline: form.headline || null,
      bio: form.bio || null,
      skills: form.skillsText.split(',').map((s) => s.trim()).filter(Boolean),
      school_or_dept: form.school_or_dept || null,
      contact_number: form.contact_number || null,
      region_code: addr.region_code || null, region_name: nameOf(regions.value, addr.region_code),
      province_code: addr.province_code || null, province_name: nameOf(provinces.value, addr.province_code),
      city_code: addr.city_code || null, city_name: nameOf(cities.value, addr.city_code),
      barangay_code: addr.barangay_code || null, barangay_name: nameOf(barangays.value, addr.barangay_code),
    }
    const res = await api<any>('/profiles/me', { method: 'PUT', body })
    if (user.value) user.value = { ...user.value, full_name: res.user.full_name }
    msg.value = 'Profile saved.'
  } catch (e: any) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <h1 class="text-2xl font-bold">My profile</h1>

    <Card>
      <CardHeader>
        <CardTitle class="text-lg">Details</CardTitle>
        <CardDescription>{{ user?.email }} · your email and phone are never shown publicly.</CardDescription>
      </CardHeader>
      <CardContent>
        <form class="space-y-4" @submit.prevent="save">
          <p v-if="msg" class="rounded-md bg-emerald-50 p-2 text-sm text-emerald-700">{{ msg }}</p>
          <p v-if="error" class="rounded-md bg-red-50 p-2 text-sm text-red-700">{{ error }}</p>

          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1.5">
              <Label for="fn">Full name</Label>
              <Input id="fn" v-model="form.full_name" required minlength="2" maxlength="100" />
            </div>
            <div class="space-y-1.5">
              <Label for="hl">Headline</Label>
              <Input id="hl" v-model="form.headline" maxlength="120" placeholder="e.g. BSIT student · poster & logo design" />
            </div>
          </div>
          <div class="space-y-1.5">
            <Label for="bio">About</Label>
            <Textarea id="bio" v-model="form.bio" rows="4" maxlength="2000" />
          </div>
          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1.5">
              <Label for="sk">Skills (comma separated)</Label>
              <Input id="sk" v-model="form.skillsText" placeholder="Photoshop, Proofreading, Algebra" />
            </div>
            <div class="space-y-1.5">
              <Label for="dept">School / department</Label>
              <Input id="dept" v-model="form.school_or_dept" maxlength="100" />
            </div>
            <div class="space-y-1.5">
              <Label for="ph">Mobile number</Label>
              <Input id="ph" v-model="form.contact_number" placeholder="09123456789" />
            </div>
          </div>

          <div>
            <p class="mb-2 text-sm font-medium">Location (PSGC)</p>
            <div class="grid gap-3 sm:grid-cols-2">
              <AppSelect v-model="addr.region_code" @change="onRegion">
                <option value="">Region</option>
                <option v-for="o in regions" :key="o.code" :value="o.code">{{ o.name }}</option>
              </AppSelect>
              <AppSelect v-model="addr.province_code" :disabled="!provinces.length" @change="onProvince">
                <option value="">Province</option>
                <option v-for="o in provinces" :key="o.code" :value="o.code">{{ o.name }}</option>
              </AppSelect>
              <AppSelect v-model="addr.city_code" :disabled="!cities.length" @change="onCity">
                <option value="">City / municipality</option>
                <option v-for="o in cities" :key="o.code" :value="o.code">{{ o.name }}</option>
              </AppSelect>
              <AppSelect v-model="addr.barangay_code" :disabled="!barangays.length">
                <option value="">Barangay</option>
                <option v-for="o in barangays" :key="o.code" :value="o.code">{{ o.name }}</option>
              </AppSelect>
            </div>
          </div>

          <Button type="submit" :disabled="saving">{{ saving ? 'Saving…' : 'Save profile' }}</Button>
        </form>
      </CardContent>
    </Card>

    <Card v-if="user?.role === 'freelancer'">
      <CardHeader>
        <CardTitle class="text-lg">Portfolio</CardTitle>
        <CardDescription>Show clients examples of your work.</CardDescription>
      </CardHeader>
      <CardContent>
        <PortfolioManager :items="data?.portfolio || []" @changed="refresh()" />
      </CardContent>
    </Card>
  </div>
</template>

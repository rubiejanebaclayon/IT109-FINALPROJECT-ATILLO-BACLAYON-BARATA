// Auto-imported helpers (Nuxt auto-imports everything exported from /utils)

export const peso = (n: number | string | null | undefined): string =>
  new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' }).format(Number(n ?? 0))

export const fdate = (d?: string | null): string =>
  d ? new Date(d).toLocaleDateString('en-PH', { year: 'numeric', month: 'short', day: 'numeric' }) : '-'

export const fdatetime = (d?: string | null): string =>
  d
    ? new Date(d).toLocaleString('en-PH', { year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
    : '-'

export const initials = (name?: string): string =>
  (name || '?').split(' ').filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join('')

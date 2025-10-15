<script setup lang="ts">
const props = defineProps<{
  readable?: string | null
  original?: string | null
  name?: string | null
}>()

const copied = reactive<Record<string, boolean>>({})
const hexPre = ref<HTMLElement | null>(null)
const asciiPre = ref<HTMLElement | null>(null)

function copyWithFeedback(key: string, text: string) {
  if (!text) return
  navigator.clipboard.writeText(text)
  copied[key] = true
  setTimeout(() => (copied[key] = false), 1500)
}

function getSelectionWithin(el: HTMLElement | null): string | null {
  if (!el || typeof window === 'undefined') return null
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) return null
  const range = sel.getRangeAt(0)
  if (!el.contains(range.startContainer) || !el.contains(range.endContainer)) return null
  const text = sel.toString()
  return text && text.trim() ? text : null
}

function copyHex() {
  const selected = getSelectionWithin(hexPre.value)
  copyWithFeedback('copy-hex', selected || hexDump.value)
}

function copyAscii() {
  const selected = getSelectionWithin(asciiPre.value)
  copyWithFeedback('copy-readable', selected || (props.readable || ''))
}

function base64ToBytes(b64: string): Uint8Array<ArrayBuffer> {
  const bin = atob(b64)
  const buffer = new ArrayBuffer(bin.length)
  const out = new Uint8Array(buffer)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out
}

const bytes = computed<Uint8Array | null>(() => {
  if (!props.original) return null
  try {
    return base64ToBytes(props.original)
  } catch {
    return null
  }
})

const byteLen = computed<number | null>(() => (bytes.value ? bytes.value.length : null))

function formatBytesCount(n: number): string {
  try {
    return new Intl.NumberFormat().format(n)
  } catch {
    return String(n)
  }
}

function downloadOriginal() {
  if (!props.original) return
  const data = base64ToBytes(props.original)
  const blob = new Blob([data], { type: 'application/octet-stream' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = props.name || 'payload.bin'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function toAscii(b: number): string {
  return b >= 0x20 && b <= 0x7e ? String.fromCharCode(b) : '.'
}

const hexDump = computed(() => {
  const arr = bytes.value
  if (!arr) return ''
  const lines: string[] = []
  const total = arr.length
  const pad = total > 0xffff ? 8 : 4
  for (let off = 0; off < total; off += 16) {
    const slice = arr.slice(off, Math.min(off + 16, total))
    const hexParts: string[] = []
    const asciiParts: string[] = []
    for (let i = 0; i < 16; i++) {
      if (i < slice.length) {
        const b = slice[i]!
        hexParts.push(b.toString(16).padStart(2, '0'))
        asciiParts.push(toAscii(b))
      } else {
        hexParts.push('  ')
        asciiParts.push(' ')
      }
    }
    // group bytes for readability: 8 + 8
    const hexGrouped = hexParts.slice(0, 8).join(' ') + '  ' + hexParts.slice(8, 16).join(' ')
    const asciiStr = asciiParts.join('')
    const offset = off.toString(16).padStart(pad, '0')
    lines.push(`${offset}:    ${hexGrouped}    ${asciiStr}`)
  }
  return lines.join('\n')
})
</script>

<template>
  <div class="space-y-3">
    <!-- Hex view with header toolbar -->
    <div>
      <div class="flex items-center justify-between mb-1">
        <div class="text-xs text-muted-foreground">
          Payload <span v-if="byteLen !== null">({{ formatBytesCount(byteLen as number) }} bytes)</span>
        </div>
        <div class="flex items-center gap-2">
          <Button variant="outline" size="sm" class="h-7 px-2" @click="copyHex">
            <Icon v-if="copied['copy-hex']" name="lucide:check" class="h-3.5 w-3.5 text-primary" />
            <Icon v-else name="lucide:copy" class="h-3.5 w-3.5" />
            <span class="ml-1">Copy Hex</span>
          </Button>
          <Button v-if="original" variant="outline" size="sm" class="h-7 px-2" @click="copyWithFeedback('copy-b64', original || '')">
            <Icon v-if="copied['copy-b64']" name="lucide:check" class="h-3.5 w-3.5 text-primary" />
            <Icon v-else name="lucide:copy" class="h-3.5 w-3.5" />
            <span class="ml-1">Copy Base64</span>
          </Button>
          <Button v-if="original" variant="outline" size="sm" class="h-7 px-2" @click="downloadOriginal">
            <Icon name="lucide:download" class="h-3.5 w-3.5" />
            <span class="ml-1">Download</span>
          </Button>
        </div>
      </div>
      <pre ref="hexPre" class="rounded border p-3 text-xs overflow-auto max-h-64 whitespace-pre"><code>{{ hexDump }}</code></pre>
    </div>

    <!-- ASCII / readable view with header toolbar -->
    <div>
      <div class="flex items-center justify-between mb-1">
        <div class="text-xs text-muted-foreground">ASCII Payload</div>
        <Button variant="outline" size="sm" class="h-7 px-2" @click="copyAscii">
          <Icon v-if="copied['copy-readable']" name="lucide:check" class="h-3.5 w-3.5 text-primary" />
          <Icon v-else name="lucide:copy" class="h-3.5 w-3.5" />
          <span class="ml-1">Copy ASCII</span>
        </Button>
      </div>
      <pre ref="asciiPre" class="rounded border p-3 text-xs overflow-auto max-h-64 whitespace-pre"><code>{{ readable || '' }}</code></pre>
    </div>
  </div>
</template>

<style scoped>
/* Ensure monospace alignment */
pre { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
</style>

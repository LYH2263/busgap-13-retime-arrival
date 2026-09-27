<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'

const rows = ref<any[]>([])
const editingId = ref<number | null>(null)
const editValue = ref('')
const editError = ref('')
const notice = ref('')
const saving = ref(false)

async function load() {
  rows.value = await api('/arrivals')
}
onMounted(load)

function startEdit(r: any) {
  editingId.value = r.id
  editValue.value = String(r.actual_arrive).replace('T', ' ')
  editError.value = ''
  notice.value = ''
}
function cancelEdit() {
  editingId.value = null
  editError.value = ''
}
function detailOf(e: any) {
  try {
    const d = JSON.parse(e?.message || '')?.detail
    return typeof d === 'string' ? d : '保存失败'
  } catch {
    return '保存失败，请检查网络后重试'
  }
}
async function save(r: any) {
  const v = editValue.value.trim()
  if (!v) { editError.value = '时刻不能为空'; return }
  saving.value = true
  try {
    await api('/arrivals/' + r.id, { method: 'PUT', body: JSON.stringify({ actual_arrive: v }) })
    editingId.value = null
    notice.value = `已保存 ${r.trip_no} · ${r.stop_name} 的到站时刻，重新检测与时间轴将按新时刻计算`
    await load()
  } catch (e) {
    editError.value = detailOf(e)
  } finally {
    saving.value = false
  }
}
</script>
<template>
  <h1>到站</h1>
  <p class="sub">各班次实际到站记录 · 点击「改」可修正到站时刻（格式 YYYY-MM-DD HH:MM）</p>
  <p v-if="notice" class="arr-ok">{{ notice }}</p>
  <div class="card">
    <table>
      <thead><tr><th>班次</th><th>站序</th><th>站点</th><th>实际到站</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.trip_no }}</td><td>{{ r.stop_seq }}</td><td>{{ r.stop_name }}</td>
          <td>
            <div v-if="editingId === r.id" class="arr-edit">
              <input
                v-model="editValue"
                class="arr-input"
                type="text"
                placeholder="2026-09-17 07:08"
                :disabled="saving"
                @keyup.enter="save(r)"
                @keyup.esc="cancelEdit"
              />
              <button class="btn-mini" :disabled="saving" @click="save(r)">保存</button>
              <button class="btn-mini" :disabled="saving" @click="cancelEdit">取消</button>
              <span v-if="editError" class="arr-err">{{ editError }}</span>
            </div>
            <span v-else class="arr-time">{{ r.actual_arrive }}</span>
          </td>
          <td>
            <button v-if="editingId !== r.id" class="btn-mini" @click="startEdit(r)">改</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

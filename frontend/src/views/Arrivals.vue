<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
const editingId = ref<number | null>(null)
const editValue = ref('')
const error = ref('')
const saving = ref(false)

async function load() {
  rows.value = await api('/arrivals')
}
onMounted(load)

function startEdit(r: any) {
  editingId.value = r.id
  editValue.value = (r.actual_arrive || '').slice(0, 16)
  error.value = ''
}
function cancelEdit() {
  editingId.value = null
  error.value = ''
}
async function save(r: any) {
  error.value = ''
  if (!editValue.value) {
    error.value = '时刻不能为空，未保存'
    return
  }
  saving.value = true
  try {
    await api('/arrivals/' + r.id, {
      method: 'PATCH',
      body: JSON.stringify({ actual_arrive: editValue.value }),
    })
    editingId.value = null
    await load()
  } catch {
    error.value = '保存失败：时刻为空或格式无法解析，记录保持改前'
  } finally {
    saving.value = false
  }
}
</script>
<template>
  <h1>到站</h1>
  <p class="sub">各班次实际到站记录 · 点击「修改」可更正到站时刻，保存后重新检测</p>
  <div class="card">
    <table>
      <thead><tr><th>班次</th><th>站序</th><th>站点</th><th>实际到站</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.trip_no }}</td><td>{{ r.stop_seq }}</td><td>{{ r.stop_name }}</td>
          <td>
            <input
              v-if="editingId === r.id"
              v-model="editValue"
              type="datetime-local"
              class="dt-input"
              :disabled="saving"
            >
            <template v-else>{{ r.actual_arrive }}</template>
          </td>
          <td>
            <template v-if="editingId === r.id">
              <button class="btn btn-sm" :disabled="saving" @click="save(r)">保存</button>
              <button class="btn btn-sm btn-ghost" :disabled="saving" @click="cancelEdit">取消</button>
            </template>
            <button v-else class="btn btn-sm" @click="startEdit(r)">修改</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="error" class="err">{{ error }}</p>
  </div>
</template>

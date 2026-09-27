<template>
  <div class="card">
    <h2>我的预约</h2>
    <table v-if="rows.length">
      <thead>
        <tr><th>科室</th><th>医生</th><th>日期</th><th>时段</th><th>状态</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id">
          <td>{{ r.dept }}</td>
          <td>{{ r.doctor }}</td>
          <td>{{ r.date }}</td>
          <td>{{ r.time }}</td>
          <td><span :class="r.status === 'BOOKED' ? 'tag b' : 'tag c'">
            {{ r.status === "BOOKED" ? "已预约" : "已取消" }}</span></td>
          <td>
            <button
              v-if="r.status === 'BOOKED'"
              class="btn ghost"
              @click="cancel(r)"
            >取消</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="muted">还没有预约，去 <a href="#/" style="color: var(--blue)">预约挂号</a> 吧</p>
    <p v-if="msg" class="msg">{{ msg }}</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import api from "../api";

const rows = ref([]);
const msg = ref("");

async function load() {
  rows.value = (await api.get("/appointments/mine")).data;
}

async function cancel(row) {
  msg.value = "";
  try {
    await api.post(`/appointments/${row.id}/cancel`);
    await load();
  } catch (e) {
    msg.value = e.response?.data?.detail ?? "取消失败";
  }
}

onMounted(load);
</script>

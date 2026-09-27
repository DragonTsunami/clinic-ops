<template>
  <div class="card">
    <h2>科室与医生</h2>
    <div class="dept-tabs">
      <button
        v-for="d in depts"
        :key="d"
        :class="{ on: d === curDept }"
        @click="curDept = d"
      >{{ d }}</button>
    </div>

    <div v-for="doc in docsByDept" :key="doc.doctor_id" style="margin-bottom: 14px">
      <div style="font-size: 15px; font-weight: 600; margin-bottom: 4px">
        {{ doc.doctor }} <span class="tag b">{{ doc.title }}</span>
      </div>
      <div class="slot-row" v-for="s in doc.slots" :key="s.schedule_id">
        <span>{{ s.date }} {{ s.time }}</span>
        <span>
          <span v-if="s.booked < s.capacity" class="muted" style="margin-right: 10px">可约</span>
          <span v-else class="muted" style="margin-right: 10px">约满</span>
          <button class="btn" :disabled="s.booked >= s.capacity" @click="book(s)">预约</button>
        </span>
      </div>
    </div>
    <p v-if="msg" class="msg">{{ msg }}</p>
    <p v-if="okMsg" class="ok">{{ okMsg }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import api from "../api";

const doctors = ref([]);
const depts = computed(() => [...new Set(doctors.value.map((d) => d.dept))]);
const curDept = ref("");
const msg = ref("");
const okMsg = ref("");

const docsByDept = computed(() => {
  const map = new Map();
  for (const s of schedules.value) {
    if (s.dept !== curDept.value) continue;
    if (!map.has(s.doctor_id))
      map.set(s.doctor_id, { doctor_id: s.doctor_id, doctor: s.doctor, title: s.title, slots: [] });
    map.get(s.doctor_id).slots.push(s);
  }
  return [...map.values()];
});

const schedules = ref([]);

async function load() {
  [doctors.value, schedules.value] = await Promise.all([
    api.get("/doctors").then((r) => r.data),
    api.get("/schedules?days=3").then((r) => r.data),
  ]);
  if (!curDept.value) curDept.value = depts.value[0] ?? "";
}

async function book(slot) {
  msg.value = "";
  okMsg.value = "";
  try {
    await api.post("/appointments", { schedule_id: slot.schedule_id });
    okMsg.value = `✅ 已预约 ${slot.date} ${slot.time} ${slot.doctor}`;
    await load();
  } catch (e) {
    msg.value = e.response?.data?.detail ?? "预约失败，请重试";
  }
}

onMounted(load);
</script>

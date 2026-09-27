<template>
  <div class="card" style="max-width: 380px; margin: 40px auto">
    <h2>注册</h2>
    <input v-model="name" placeholder="姓名" maxlength="32" />
    <input v-model="phone" placeholder="手机号" maxlength="11" />
    <input v-model="password" type="password" placeholder="密码（≥6位）" @keyup.enter="submit" />
    <p v-if="msg" class="msg">{{ msg }}</p>
    <button class="btn" style="width: 100%" @click="submit">注册并登录</button>
    <p class="muted" style="margin-top: 12px; text-align: center">
      已有账号？<a href="#/login" style="color: var(--blue)">登录</a>
    </p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import api from "../api";

const name = ref("");
const phone = ref("");
const password = ref("");
const msg = ref("");
const router = useRouter();

async function submit() {
  msg.value = "";
  try {
    const { data } = await api.post("/auth/register", {
      name: name.value,
      phone: phone.value,
      password: password.value,
    });
    localStorage.setItem("token", data.token);
    localStorage.setItem("name", data.name);
    router.push("/");
  } catch (e) {
    msg.value = e.response?.data?.detail ?? "注册失败";
  }
}
</script>

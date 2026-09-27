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
  if (!/^1\d{10}$/.test(phone.value)) {
    msg.value = "手机号格式不正确：需 11 位、以 1 开头";
    return;
  }
  if (password.value.length < 6) {
    msg.value = "密码至少 6 位";
    return;
  }
  if (!name.value.trim()) {
    msg.value = "请填写姓名";
    return;
  }
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

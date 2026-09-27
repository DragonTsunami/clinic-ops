<template>
  <div class="card" style="max-width: 380px; margin: 40px auto">
    <h2>登录</h2>
    <input v-model="phone" placeholder="手机号" maxlength="11" />
    <input v-model="password" type="password" placeholder="密码" @keyup.enter="submit" />
    <p v-if="msg" class="msg">{{ msg }}</p>
    <button class="btn" style="width: 100%" @click="submit">登录</button>
    <p class="muted" style="margin-top: 12px; text-align: center">
      没有账号？<a href="#/register" style="color: var(--blue)">注册</a>
    </p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import api from "../api";

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
  if (!password.value) {
    msg.value = "请输入密码";
    return;
  }
  try {
    const { data } = await api.post("/auth/login", {
      phone: phone.value,
      password: password.value,
    });
    localStorage.setItem("token", data.token);
    localStorage.setItem("name", data.name);
    router.push("/");
  } catch (e) {
    msg.value = e.response?.data?.detail ?? "登录失败";
  }
}
</script>

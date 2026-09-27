<template>
  <header>
    <div class="brand">🩺 青衫诊所 · 预约挂号</div>
    <div class="user" v-if="name" @click="logout">{{ name }} · 退出</div>
    <div class="user" v-else @click="$router.push('/login')">登录 / 注册</div>
  </header>
  <main>
    <router-view />
  </main>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

const name = ref(localStorage.getItem("name"));
const router = useRouter();

function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("name");
  name.value = null;
  router.push("/login");
}
</script>

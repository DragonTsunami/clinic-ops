import { createRouter, createWebHashHistory } from "vue-router";
import Booking from "./views/Booking.vue";
import Login from "./views/Login.vue";
import Mine from "./views/Mine.vue";
import Register from "./views/Register.vue";

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", component: Booking, meta: { auth: true } },
    { path: "/mine", component: Mine, meta: { auth: true } },
    { path: "/login", component: Login },
    { path: "/register", component: Register },
  ],
});

router.beforeEach((to) => {
  if (to.meta.auth && !localStorage.getItem("token")) return "/login";
});

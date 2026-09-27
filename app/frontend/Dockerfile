# syntax=docker/dockerfile:1
# ---- 构建阶段：node 编译 Vue 产物 ----
FROM node:22-alpine AS build
WORKDIR /build
COPY package.json ./
RUN npm install --registry=https://registry.npmmirror.com
COPY . .
RUN npm run build

# ---- 运行阶段：nginx 托管静态 + 反代 /api ----
FROM nginx:1.27-alpine
COPY --from=build /build/dist /usr/share/nginx/html
COPY nginx-frontend.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=3s --retries=4 \
  CMD wget -qO /dev/null http://127.0.0.1/ || exit 1

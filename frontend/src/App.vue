<template>
  <el-container class="app-container">
    <el-header>
      <div class="header-content">
        <h1 class="logo">工作日志追踪</h1>
        <el-menu
          :default-active="activeMenu"
          mode="horizontal"
          router
          class="nav-menu"
        >
          <el-menu-item index="/">仪表盘</el-menu-item>
          <el-menu-item index="/journals">日志</el-menu-item>
          <el-menu-item index="/config">配置</el-menu-item>
          <el-menu-item index="/stats">统计</el-menu-item>
        </el-menu>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background-color: #f5f7fa;
}

.app-container {
  min-height: 100vh;
}

.el-header {
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
}

.header-content {
  display: flex;
  align-items: center;
  height: 60px;
}

.logo {
  font-size: 18px;
  margin: 0;
  margin-right: 40px;
  color: #303133;
  white-space: nowrap;
}

.nav-menu {
  border-bottom: none !important;
}

.el-main {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}
</style>

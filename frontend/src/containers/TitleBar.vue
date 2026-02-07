<template>
  <div class="title-bar" data-tauri-drag-region>
    <div class="title-bar-content">
      <span class="app-title">LanGit</span>
    </div>
    <div class="title-bar-actions" @click.self="toggleUserMenu">
      <button class="user-button" @click="toggleUserMenu">
        <span class="user-avatar">{{ userInitials }}</span>
        <span class="user-name">{{ currentUser?.username }}</span>
      </button>
      
      <!-- 用户信息下拉菜单 -->
      <div v-if="showUserMenu" class="user-menu">
        <div class="user-menu-header">
          <div class="user-avatar-large">{{ userInitials }}</div>
          <div class="user-info">
            <div class="user-full-name">{{ currentUser?.full_name || currentUser?.username }}</div>
            <div class="user-email">{{ currentUser?.email }}</div>
          </div>
        </div>
        <div class="user-menu-divider"></div>
        <div class="user-menu-actions">
          <button class="user-menu-item" @click="handleLogout">
            <span class="menu-item-icon">📤</span>
            <span class="menu-item-text">退出登录</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/stores/user';

// 获取用户状态
const userStore = useUserStore();
const currentUser = computed(() => userStore.currentUser);
const isLoggedIn = computed(() => userStore.isLoggedIn);

// 路由
const router = useRouter();

// 下拉菜单显示状态
const showUserMenu = ref(false);

// 计算用户首字母
const userInitials = computed(() => {
  if (!currentUser.value) return '?';
  return currentUser.value.username.charAt(0).toUpperCase();
});

// 切换用户菜单显示
const toggleUserMenu = () => {
  if (isLoggedIn.value) {
    showUserMenu.value = !showUserMenu.value;
  }
};

// 关闭用户菜单
const closeUserMenu = () => {
  showUserMenu.value = false;
};

// 退出登录
const handleLogout = () => {
  userStore.logout();
  showUserMenu.value = false;
  // 立即重定向到登录页面
  router.push('/login');
};

// 点击外部关闭菜单
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement;
  if (!target.closest('.title-bar-actions')) {
    closeUserMenu();
  }
};

// 监听点击事件
onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.title-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 40px;
  background-color: #2c3e50;
  color: white;
  padding: 0 16px;
  user-select: none;
}

.title-bar-content {
  display: flex;
  align-items: center;
}

.app-title {
  font-size: 16px;
  font-weight: bold;
}

.title-bar-actions {
  display: flex;
  align-items: center;
  position: relative;
}

.user-button {
  display: flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  border: none;
  color: white;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 14px;
  transition: background-color 0.2s;
}

.user-button:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background-color: #3498db;
  color: white;
  font-weight: bold;
  font-size: 12px;
}

.user-avatar-large {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background-color: #3498db;
  color: white;
  font-weight: bold;
  font-size: 20px;
}

.user-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background-color: white;
  color: #333;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
  min-width: 240px;
  z-index: 1000;
  overflow: hidden;
}

.user-menu-header {
  display: flex;
  align-items: center;
  padding: 16px;
  gap: 12px;
  background-color: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.user-info {
  flex: 1;
}

.user-full-name {
  font-weight: bold;
  font-size: 15px;
  margin-bottom: 4px;
}

.user-email {
  font-size: 13px;
  color: #666;
}

.user-menu-divider {
  height: 1px;
  background-color: #e9ecef;
  margin: 0;
}

.user-menu-actions {
  padding: 8px;
}

.user-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
  text-align: left;
}

.user-menu-item:hover {
  background-color: #f0f2f5;
}

.menu-item-icon {
  font-size: 16px;
}

.menu-item-text {
  flex: 1;
}
</style>
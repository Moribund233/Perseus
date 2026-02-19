<script setup lang="ts">
import { useThemeStore, presetColorThemes, layoutDensityPresets } from '../../stores'

/**
 * 主题设置组件
 *
 * 提供颜色主题和布局密度的选择功能
 */

const themeStore = useThemeStore()

/**
 * 处理颜色主题切换
 * @param themeId - 主题ID
 */
const handleColorThemeChange = (themeId: string): void => {
  themeStore.switchColorTheme(themeId)
}

/**
 * 处理布局密度切换
 * @param densityId - 布局密度ID
 */
const handleLayoutDensityChange = (densityId: string): void => {
  themeStore.switchLayoutDensity(densityId)
}
</script>

<template>
  <div class="config-section">
    <!-- 颜色主题选择 -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">颜色主题</h2>
      </div>

      <div class="theme-grid">
        <div
          v-for="theme in presetColorThemes"
          :key="theme.id"
          class="theme-item"
          :class="{ active: themeStore.currentColorThemeId === theme.id }"
          @click="handleColorThemeChange(theme.id)"
        >
          <div
            class="theme-preview"
            :style="{ backgroundColor: theme.previewColor }"
          ></div>
          <span class="theme-name">{{ theme.name }}</span>
        </div>
      </div>
    </div>

    <!-- 布局密度选择 -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">布局密度</h2>
      </div>

      <div class="density-grid">
        <div
          v-for="density in layoutDensityPresets"
          :key="density.id"
          class="density-item"
          :class="{ active: themeStore.currentLayoutDensityId === density.id }"
          @click="handleLayoutDensityChange(density.id)"
        >
          <div class="density-preview" :class="`density-preview-${density.id}`">
            <div class="preview-block"></div>
            <div class="preview-block"></div>
            <div class="preview-block"></div>
          </div>
          <span class="density-name">{{ density.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

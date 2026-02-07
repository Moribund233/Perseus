<template>
  <Tool title="调色板" id="colorPalette" :message-targets="['Example1']">
    <template #default="{ }">
      <div class="color-palette-content">
        <h3>颜色选择器</h3>
        <p>选择一个颜色来改变页面背景</p>
      
      <div class="color-grid">
        <div 
          v-for="color in colors" 
          :key="color"
          class="color-item"
          :class="{ 'selected': selectedColor === color }"
          :style="{ backgroundColor: color }"
          @click="selectColor(color)"
        >
          <span class="color-value">{{ color }}</span>
        </div>
      </div>
      
      <div class="custom-color-section">
        <h4>自定义颜色</h4>
        <div class="custom-color-input">
          <input 
            type="color" 
            v-model="customColor" 
            class="color-picker"
            @input="selectCustomColor"
          />
          <input 
            type="text" 
            v-model="customColor" 
            class="color-text"
            placeholder="#000000"
            @input="selectCustomColor"
          />
        </div>
      </div>
      
      <div class="selected-color-section">
        <h4>当前选择</h4>
        <div class="selected-color-display">
          <div 
            class="selected-color-preview" 
            :style="{ backgroundColor: selectedColor }"
          ></div>
          <span class="selected-color-value">{{ selectedColor }}</span>
        </div>
        <button 
          class="apply-button" 
          @click="applyColor"
        >
          应用颜色
        </button>
      </div>
    </div>
    </template>
  </Tool>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import Tool from '@/components/public/Tool.vue';
import { sendMessageToTargets } from '@/utils/eventBus';

const colors = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
  '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
  '#BB8FCE', '#85C1E2', '#F8C471', '#82E0AA',
  '#EC7063', '#85C1E2', '#F8C471', '#82E0AA',
  '#3498DB', '#E74C3C', '#2ECC71', '#F39C12',
  '#9B59B6', '#1ABC9C', '#E67E22', '#34495E'
];

const selectedColor = ref('#FFFFFF');
const customColor = ref('#FFFFFF');

const selectColor = (color: string) => {
  selectedColor.value = color;
  customColor.value = color;
};

const selectCustomColor = () => {
  selectedColor.value = customColor.value;
};

const applyColor = () => {
  sendMessageToTargets(
    'colorPalette',
    ['Example1'],
    'colorChanged',
    { color: selectedColor.value }
  );
  console.log(`应用颜色: ${selectedColor.value}`);
};
</script>

<style scoped>
.color-palette-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
}

h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
}

p {
  margin: 0;
  line-height: 1.5;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.color-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  padding: 10px;
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.color-item {
  width: 100%;
  aspect-ratio: 1;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
  position: relative;
  overflow: hidden;
  border: 2px solid transparent;
}

.color-item:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.color-item.selected {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-light);
  transform: scale(1.05);
}

.color-value {
  position: absolute;
  bottom: 4px;
  left: 4px;
  font-size: 10px;
  color: white;
  background-color: rgba(0, 0, 0, 0.5);
  padding: 2px 4px;
  border-radius: 2px;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.color-item:hover .color-value {
  opacity: 1;
}

.custom-color-section {
  padding: 16px;
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.custom-color-input {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 8px;
}

.color-picker {
  width: 60px;
  height: 40px;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  background-color: transparent;
}

.color-text {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background-color: var(--color-bg);
  color: var(--color-text);
  font-size: 14px;
}

.color-text:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-light);
}

.selected-color-section {
  padding: 16px;
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.selected-color-display {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 8px 0;
}

.selected-color-preview {
  width: 60px;
  height: 40px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

.selected-color-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
}

.apply-button {
  width: 100%;
  padding: 10px;
  margin-top: 12px;
  background-color: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all var(--transition-fast);
}

.apply-button:hover {
  background-color: var(--color-primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.apply-button:active {
  transform: translateY(0);
}
</style>

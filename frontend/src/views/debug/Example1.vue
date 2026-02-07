<template>
    <div class="example1">
        <h1>Example 1</h1>
    </div>
    <div class="example1-content">
        <p>这是一个示例1的内容区域。</p>
        
        <!-- 测试容器，用于展示调色板工具的效果 -->
        <div class="test-container" :style="{ backgroundColor: containerColor }">
            <h2>测试容器</h2>
            <p>这个容器的背景色会根据调色板工具的选择而改变</p>
            <div class="color-info">
                <span>当前颜色: {{ containerColor }}</span>
            </div>
        </div>
    </div>
    <div class="example1-footer">
        <p>这是一个示例1的页脚区域。</p>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { onAnyMessage } from '@/utils/eventBus';

const containerColor = ref('#ffffff');

let unsubscribe: (() => void) | null = null;

const handleColorChange = (data: any) => {
  if (data.color) {
    containerColor.value = data.color;
    console.log(`[Example1] 收到颜色变更消息: ${data.color}`);
  }
};

onMounted(() => {
  unsubscribe = onAnyMessage((message) => {
    if (message.type === 'colorChanged' && message.source === 'colorPalette') {
      handleColorChange(message.data);
    }
  });
});

onUnmounted(() => {
  if (unsubscribe) {
    unsubscribe();
  }
});
</script>

<style scoped>
.example1 {
    padding: 20px;
    text-align: center;
}

.example1-content {
    padding: 20px;
    max-width: 800px;
    margin: 0 auto;
}

.test-container {
    padding: 30px;
    margin: 20px 0;
    border-radius: 10px;
    background-color: #ffffff;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    transition: background-color 0.3s ease;
    text-align: center;
}

.test-container h2 {
    margin-top: 0;
    color: #333;
}

.test-container p {
    color: rgba(0, 0, 0, 0.8);
    margin-bottom: 20px;
}

.color-info {
    background-color: rgba(0, 0, 0, 0.1);
    padding: 10px;
    border-radius: 5px;
    display: inline-block;
    margin-top: 10px;
    font-weight: bold;
}

.example1-footer {
    padding: 20px;
    text-align: center;
    color: #666;
    border-top: 1px solid #eee;
    margin-top: 40px;
}
</style>

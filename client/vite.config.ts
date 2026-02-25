import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import type { UserConfig } from "vite";

// @ts-expect-error process is a nodejs global
const host = process.env.TAURI_DEV_HOST;

// https://vite.dev/config/
export default defineConfig((): UserConfig => ({
  plugins: [
    vue({
      // 开发模式优化
      template: {
        compilerOptions: {
          // 跳过不必要的类型检查
          hoistStatic: true,
          // 启用缓存
          cacheHandlers: true,
        },
      },
    }),
  ],

  resolve: {
    alias: {
      // @ts-ignore
      "@": new URL("./src", import.meta.url).pathname,
    },
  },

  // ==================== 性能优化配置 ====================

  // 构建优化
  build: {
    // 启用代码分割
    rollupOptions: {
      output: {
        manualChunks: {
          // 将第三方库单独打包
          vendor: ["vue", "vue-router", "pinia"],
        },
      },
    },
    // 启用压缩
    minify: "terser",
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
  },

  // 优化依赖预构建
  optimizeDeps: {
    include: ["vue", "vue-router", "pinia"],
    // 禁用依赖扫描，加快启动速度
    force: false,
  },

  // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
  //
  // 1. prevent Vite from obscuring rust errors
  clearScreen: false,
  // 2. tauri expects a fixed port, fail if that port is not available
  server: {
    port: 1420,
    strictPort: true,
    host: host || false,
    hmr: host
      ? {
          protocol: "ws",
          host,
          port: 1421,
        }
      : undefined,
    watch: {
      // 3. tell Vite to ignore watching `src-tauri` and `server` directories
      ignored: ["**/src-tauri/**", "**/server/**"],
    },
  },

  // ==================== 开发模式优化 ====================

  // 启用 CSS 代码分割
  css: {
    devSourcemap: false, // 禁用 CSS sourcemap 提高性能
  },

  // 启用预渲染
  preview: {
    port: 1420,
    strictPort: true,
  },
}));

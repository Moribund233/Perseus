import { createApp } from "vue";
import { createPinia } from "pinia";
import piniaPluginPersistedstate from "pinia-plugin-persistedstate";
import "./styles/style.css";
import "./styles/variables.css";
import "./styles/containers.css";
import "./styles/scrollbar.css";
import "./utils/quickSettingMethods";
import App from "./App.vue";
import router from "./router/index";

// 创建Pinia实例
const pinia = createPinia();
// 使用持久化插件
pinia.use(piniaPluginPersistedstate);

const app = createApp(App);
app.use(pinia);
app.use(router);
app.mount("#app");
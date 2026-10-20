import "$/styles/style.scss";
import "@popperjs/core";
import "toastify-js/src/toastify.css";
import "bootstrap/js/dist/dropdown";
import "bootstrap/js/dist/collapse";
import App from "$/App.svelte";
import { mount } from "svelte";
import { configureFabric } from "$/defaults";
import { initializeDesktop, onNativeEvent } from "$/desktop/bridge";
import "$/desktop/studio.scss";
import { fontCache } from "$/stores";

configureFabric();
// Native enumerates installed fonts after the first editor frame; the picker
// starts with bundled/default families and fills in when that event arrives.
onNativeEvent((message) => {
  if (message.event === "fonts" && message.families) {
    fontCache.set(["Noto Sans Variable", ...message.families]);
  }
});
initializeDesktop().catch(console.error);

const app = mount(App, {
  target: document.getElementById("app")!,
});

export default app;

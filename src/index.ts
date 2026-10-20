import "$/styles/style.scss";
import "@popperjs/core";
import "toastify-js/src/toastify.css";
import "bootstrap/js/dist/dropdown";
import "bootstrap/js/dist/collapse";
import App from "$/App.svelte";
import { mount } from "svelte";
import { configureFabric } from "$/defaults";
import { initializeDesktop } from "$/desktop/bridge";
import "$/desktop/studio.scss";
import { fontCache } from "$/stores";

configureFabric();
initializeDesktop().then((families) => {
  if (families) fontCache.set(["Noto Sans Variable", ...families]);
}).catch(console.error);

const app = mount(App, {
  target: document.getElementById("app")!,
});

export default app;

<script lang="ts">
  import { onMount } from "svelte";
  import LabelDesigner from "$/components/LabelDesigner.svelte";
  import PrinterConnector from "$/components/PrinterConnector.svelte";
  import DebugStuff from "$/components/DebugStuff.svelte";
  import TemplateLibrary from "$/desktop/TemplateLibrary.svelte";
  import SidebarIcon from "$/desktop/SidebarIcon.svelte";
  import MdIcon from "$/components/basic/MdIcon.svelte";
  import { nativeRequest, onNativeEvent } from "$/desktop/bridge";
  let diagnostics = $state(false);
  let designer = $state<LabelDesigner>();
  let library = $state<TemplateLibrary>();
  let update = $state<{ version: string; tag: string }>();
  let updateState = $state<"idle" | "starting" | "ready" | "failed">("idle");
  let updateMessage = $state("");

  onMount(() =>
    onNativeEvent((message) => {
      if (message.event === "update" && message.version && message.tag) {
        update = { version: message.version, tag: message.tag };
        updateState = "idle";
      } else if (message.event === "updateProgress") {
        updateState = message.state === "ready" ? "ready" : "failed";
        updateMessage = message.message ?? "";
      }
    }),
  );

  const installUpdate = async () => {
    if (!update) return;
    updateState = "starting";
    updateMessage = "";
    try {
      await nativeRequest("updateApp", { tag: update.tag });
    } catch (error) {
      updateState = "failed";
      updateMessage = String(error instanceof Error ? error.message : error);
    }
  };
  const restart = () => nativeRequest("quit").catch(console.error);
</script>

<main class="studio-workspace">
  <TemplateLibrary
    bind:this={library}
    exportLabel={() => designer!.exportLabel()}
    loadLabel={(label) => designer!.loadLabel(label)}>
    {#snippet controls(openLibrary, openSave, notice)}
      <header class="studio-workspace-header">
        <div class="studio-heading-group">
          <button
            class="btn studio-sidebar-trigger"
            onclick={openLibrary}
            data-action="templates"
            aria-label="Open template sidebar"
            aria-haspopup="dialog"
            aria-controls="studio-template-drawer"
            title="Templates · open sidebar"><SidebarIcon /></button>
          <h1 class="studio-editor-title">Label editor</h1>
        </div>
        <div class="studio-header-actions">
          <span class="studio-save-notice" role="status">{notice}</span>
          <button
            class="btn btn-sm btn-secondary studio-save-template"
            onclick={openSave}
            data-action="save-template"
            title="Save as template · Ctrl+S"><MdIcon icon="bookmark_add" /> Save as template</button>
          <div class="studio-printer"><PrinterConnector /></div>
        </div>
      </header>
    {/snippet}
  </TemplateLibrary>
  <LabelDesigner bind:this={designer} saveTemplate={() => library?.openSave()} />
  {#if update}
    <div class="studio-update" role="status" data-testid="update-banner">
      <MdIcon icon={updateState === "ready" ? "check_circle" : "system_update_alt"} />
      {#if updateState === "ready"}
        <span>Updated to {update.version}. Restart to use the new version.</span>
        <button class="btn btn-sm btn-primary" onclick={restart} data-action="update-restart">Restart</button>
      {:else}
        <span>
          NiimStudio {update.version} is available.
          {#if updateState === "failed"}<span class="studio-update-error">{updateMessage}</span>{/if}
        </span>
        <button
          class="btn btn-sm btn-primary"
          onclick={installUpdate}
          disabled={updateState === "starting"}
          data-action="update-now">
          {updateState === "starting" ? "Updating…" : "Update now"}
        </button>
      {/if}
      <button
        class="btn btn-sm btn-link studio-update-later"
        onclick={() => (update = undefined)}
        data-action="update-later">Later</button>
    </div>
  {/if}
  <footer class="studio-footer">
    <span><strong>NiimStudio</strong> <span class="studio-footer-separator">·</span> Local label workspace</span>
    <button class="btn btn-link btn-sm" onclick={() => (diagnostics = true)}>Diagnostics</button>
  </footer>
</main>

{#if diagnostics}<DebugStuff bind:show={diagnostics} />{/if}

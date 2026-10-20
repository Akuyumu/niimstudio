<script lang="ts">
  import LabelDesigner from "$/components/LabelDesigner.svelte";
  import PrinterConnector from "$/components/PrinterConnector.svelte";
  import DebugStuff from "$/components/DebugStuff.svelte";
  import TemplateLibrary from "$/desktop/TemplateLibrary.svelte";
  import SidebarIcon from "$/desktop/SidebarIcon.svelte";
  import MdIcon from "$/components/basic/MdIcon.svelte";
  let diagnostics = $state(false);
  let designer = $state<LabelDesigner>();
  let library = $state<TemplateLibrary>();
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
  <footer class="studio-footer">
    <span><strong>NiimStudio</strong> <span class="studio-footer-separator">·</span> Local label workspace</span>
    <button class="btn btn-link btn-sm" onclick={() => (diagnostics = true)}>Diagnostics</button>
  </footer>
</main>

{#if diagnostics}<DebugStuff bind:show={diagnostics} />{/if}

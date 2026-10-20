<script lang="ts">
  import { onMount, type Snippet } from "svelte";

  let {
    show = $bindable(),
    title,
    onClose,
    dismissible = true,
    wide = false,
    children,
    footer,
  }: {
    show: boolean;
    title: string;
    onClose?: () => void;
    dismissible?: boolean;
    wide?: boolean;
    children: Snippet;
    footer?: Snippet;
  } = $props();
  let dialog: HTMLDialogElement;
  let mounted = $state(false);
  let completed = true;

  const finish = () => {
    if (completed || !dialog) return;
    completed = true;
    delete dialog.dataset.modalReady;
    show = false;
    onClose?.();
  };
  export const hide = () => {
    if (!dismissible || !dialog) return;
    if (dialog.open) dialog.close();
    finish();
  };
  const cancel = (event: Event) => {
    event.preventDefault();
    hide();
  };
  const closed = () => {
    if (dialog && !dialog.open) finish();
  };
  const outside = (event: PointerEvent) => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (
      event.clientX < bounds.left ||
      event.clientX > bounds.right ||
      event.clientY < bounds.top ||
      event.clientY > bounds.bottom
    )
      hide();
  };

  onMount(() => {
    const element = dialog;
    mounted = true;
    return () => {
      completed = true;
      if (element.open) element.close();
    };
  });
  $effect(() => {
    if (!mounted || !dialog) return;
    if (show && !dialog.open) {
      completed = false;
      dialog.showModal();
      dialog.dataset.modalReady = "true";
      // WebKit can retain the closed dialog's hidden focus state on reuse.
      const focusTarget =
        dialog.querySelector<HTMLElement>("[data-modal-autofocus]") ??
        dialog.querySelector<HTMLButtonElement>(".btn-close:not(:disabled)") ??
        dialog;
      focusTarget.focus({ preventScroll: true });
    } else if (!show && dialog.open) {
      dialog.close();
      finish();
    }
  });
</script>

<dialog
  bind:this={dialog}
  class="modal studio-native-modal"
  class:show
  class:studio-native-modal-wide={wide}
  aria-label={title}
  tabindex="-1"
  oncancel={cancel}
  onclose={closed}
  onpointerdown={outside}>
  <div class="modal-content">
    <div class="modal-header">
      <h1 class="modal-title fs-5">{title}</h1>
      <button aria-label="Dismiss" type="button" class="btn-close" disabled={!dismissible} onclick={hide}></button>
    </div>
    <div class="modal-body">{@render children()}</div>
    {#if footer}<div class="modal-footer">{@render footer()}</div>{/if}
  </div>
</dialog>

<style>
  dialog.studio-native-modal {
    inset: 0;
    margin: auto;
    padding: 0;
    border: 0;
    border-radius: 10px;
    width: min(500px, calc(100vw - 32px));
    max-width: none;
    height: fit-content;
    max-height: calc(100dvh - 32px);
    overflow: auto;
    background: transparent;
    color: inherit;
    overscroll-behavior: contain;
  }
  dialog.studio-native-modal[open] {
    display: block;
  }
  dialog.studio-native-modal-wide {
    width: min(800px, calc(100vw - 32px));
  }
  dialog::backdrop {
    background: #0008;
  }
</style>

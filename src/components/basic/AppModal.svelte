<script lang="ts">
  import Modal from "bootstrap/js/dist/modal";
  import { onDestroy, onMount, type Snippet } from "svelte";

  interface Props {
    show: boolean;
    title: string;
    onClose?: () => void;
    dismissible?: boolean;
    wide?: boolean;
    children: Snippet;
    footer?: Snippet;
  }

  let { show = $bindable(), title, onClose, dismissible = true, wide = false, children, footer }: Props = $props();

  let modalEl: HTMLElement;
  let modal: Modal;
  let fullyShown = false;
  let fullyHidden = false;
  const onShown = () => {
    fullyShown = true;
    modalEl.querySelector<HTMLElement>("[data-modal-autofocus]")?.focus();
  };
  const onHide = (event: Event) => {
    if (!dismissible) {
      event.preventDefault();
      return;
    }
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
  };
  const onHidden = () => {
    fullyHidden = true;
    onClose?.();
    show = false;
  };

  onMount(() => {
    modal = new Modal(modalEl);
    modal.show();

    modalEl.addEventListener("hide.bs.modal", onHide);
    modalEl.addEventListener("shown.bs.modal", onShown);
    modalEl.addEventListener("hidden.bs.modal", onHidden);
  });

  onDestroy(() => {
    if (modal) {
      modalEl.removeEventListener("hide.bs.modal", onHide);
      modalEl.removeEventListener("shown.bs.modal", onShown);
      modalEl.removeEventListener("hidden.bs.modal", onHidden);
      if (fullyHidden) modal.dispose();
      else {
        // Bootstrap's transition callbacks still need the instance until hidden.
        modalEl.addEventListener("hidden.bs.modal", () => modal.dispose(), { once: true });
        if (fullyShown) modal.hide();
        else modalEl.addEventListener("shown.bs.modal", () => modal.hide(), { once: true });
      }
    }
  });

  export const hide = () => {
    if (modal) {
      if (fullyShown) modal.hide();
      else modalEl.addEventListener("shown.bs.modal", () => modal.hide(), { once: true });
    }
  };
</script>

<div bind:this={modalEl} class="modal fade" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered {wide ? 'modal-lg' : ''}">
    <div class="modal-content">
      <div class="modal-header">
        <h1 class="modal-title fs-5">{title}</h1>
        <button aria-label="Dismiss" type="button" class="btn-close" disabled={!dismissible} data-bs-dismiss="modal"
        ></button>
      </div>

      <div class="modal-body">
        {@render children()}
      </div>

      {#if footer}
        <div class="modal-footer">
          {@render footer()}
        </div>
      {/if}
    </div>
  </div>
</div>

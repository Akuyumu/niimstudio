<script lang="ts">
  import MdIcon from "$/components/basic/MdIcon.svelte";

  interface Props {
    propName: string;
    savedValue: any;
    value: any;
    onClick: (key: string, value: any) => void;
  }

  let { propName, savedValue, value, onClick }: Props = $props();
</script>

<button
  class="btn btn-sm btn-outline-secondary param-lock-btn"
  aria-label={savedValue !== undefined ? "Stop remembering this print setting" : "Remember this print setting"}
  title={savedValue !== undefined
    ? "This value is remembered for future previews. Click to stop remembering it. This is not a printer security lock."
    : "Remember this value for future print previews on this computer. This is not a printer security lock."}
  onclick={() => onClick(propName, value)}>
  {#if savedValue !== undefined}
    <MdIcon icon="lock" class="text-warning" />
  {:else}
    <MdIcon icon="lock_open" />
  {/if}
</button>

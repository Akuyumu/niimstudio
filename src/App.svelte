<script lang="ts">
  import MainPage from "$/components/MainPage.svelte";
  import StudioPage from "$/desktop/StudioPage.svelte";
  import { isNative } from "$/desktop/bridge";
</script>

{#if isNative}<StudioPage />{:else}<MainPage />{/if}

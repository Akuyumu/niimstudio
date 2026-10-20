<script lang="ts">
  let { size = 22 }: { size?: number } = $props();
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="1.7"
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden="true">
  <rect x="3" y="4" width="18" height="16" rx="2.5" />
  <path d="M9 4v16M14 9l3 3-3 3" />
</svg>

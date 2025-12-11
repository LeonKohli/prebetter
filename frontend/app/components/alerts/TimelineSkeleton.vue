<script setup lang="ts">
/**
 * AlertsTimelineSkeleton - SSR placeholder for AlertsTimeline
 *
 * This component renders during SSR to maintain consistent component tree count,
 * preventing Reka UI hydration ID mismatches. It matches the visual structure
 * of AlertsTimeline so there's no layout shift during hydration.
 */
</script>

<template>
  <Card class="!py-3 !gap-2">
    <CardContent class="!px-4">
      <div class="flex items-center justify-between mb-2">
        <Skeleton class="h-4 w-24" />
        <Skeleton class="h-3 w-16" />
      </div>

      <!-- Chart skeleton - matches 180px desktop height -->
      <div class="h-[180px] bg-muted/30 rounded animate-pulse flex items-end justify-around gap-1 p-4">
        <!-- Fake bar chart bars -->
        <Skeleton class="w-full h-[40%] rounded-t rounded-b-none" />
        <Skeleton class="w-full h-[70%] rounded-t rounded-b-none" />
        <Skeleton class="w-full h-[55%] rounded-t rounded-b-none" />
        <Skeleton class="w-full h-[85%] rounded-t rounded-b-none" />
        <Skeleton class="w-full h-[60%] rounded-t rounded-b-none" />
        <Skeleton class="w-full h-[45%] rounded-t rounded-b-none" />
        <Skeleton class="w-full h-[75%] rounded-t rounded-b-none" />
        <Skeleton class="w-full h-[50%] rounded-t rounded-b-none" />
      </div>

      <Skeleton class="h-3 w-48 mt-2 mx-auto" />
    </CardContent>
  </Card>
</template>

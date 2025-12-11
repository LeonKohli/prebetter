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
        <div class="h-4 w-24 bg-muted rounded animate-pulse" />
        <div class="h-3 w-16 bg-muted rounded animate-pulse" />
      </div>

      <!-- Chart skeleton - matches 180px desktop height -->
      <div class="h-[180px] bg-muted/30 rounded animate-pulse flex items-end justify-around gap-1 p-4">
        <!-- Fake bar chart bars -->
        <div class="w-full h-[40%] bg-muted/50 rounded-t" />
        <div class="w-full h-[70%] bg-muted/50 rounded-t" />
        <div class="w-full h-[55%] bg-muted/50 rounded-t" />
        <div class="w-full h-[85%] bg-muted/50 rounded-t" />
        <div class="w-full h-[60%] bg-muted/50 rounded-t" />
        <div class="w-full h-[45%] bg-muted/50 rounded-t" />
        <div class="w-full h-[75%] bg-muted/50 rounded-t" />
        <div class="w-full h-[50%] bg-muted/50 rounded-t" />
      </div>

      <div class="h-3 w-48 bg-muted rounded animate-pulse mt-2 mx-auto" />
    </CardContent>
  </Card>
</template>

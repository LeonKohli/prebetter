<script setup lang="ts">
import type { Column } from '@tanstack/vue-table'
import type { Alert } from '~/composables/useAlerts'

interface Option {
  label: string
  value: string
  icon?: string
}

interface Props {
  column?: Column<Alert, unknown>
  title?: string
  options: Option[]
}

const props = defineProps<Props>()
const facets = computed(() => props.column?.getFacetedUniqueValues())
const selectedValues = computed(() => new Set(props.column?.getFilterValue() as string[]))

const triggerId = computed(() => `faceted-filter-${props.title?.toLowerCase()}-trigger`)
const contentId = computed(() => `faceted-filter-${props.title?.toLowerCase()}-content`)
</script>

<template>
  <Popover>
    <PopoverTrigger :id="triggerId" as-child>
      <Button variant="outline" size="sm" class="h-8 border-dashed">
        <Icon name="lucide:plus-circle" class="w-4 h-4 mr-2" />
        {{ title }}
        <template v-if="selectedValues.size > 0">
          <Separator orientation="vertical" class="h-4 mx-2" />
          <Badge
            variant="secondary"
            class="px-1 font-normal rounded-sm lg:hidden"
          >
            {{ selectedValues.size }}
          </Badge>
          <div class="hidden space-x-1 lg:flex">
            <Badge
              v-if="selectedValues.size > 2"
              variant="secondary"
              class="px-1 font-normal rounded-sm"
            >
              {{ selectedValues.size }} selected
            </Badge>
            <template v-else>
              <Badge
                v-for="option in options.filter((option) => selectedValues.has(option.value))"
                :key="option.value"
                variant="secondary"
                class="px-1 font-normal rounded-sm"
              >
                {{ option.label }}
              </Badge>
            </template>
          </div>
        </template>
      </Button>
    </PopoverTrigger>
    <PopoverContent :id="contentId" class="w-[200px] p-0" align="start">
      <Command>
        <CommandInput :placeholder="title" />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup>
            <CommandItem
              v-for="option in options"
              :key="option.value"
              :value="option"
              @select="() => {
                const isSelected = selectedValues.has(option.value)
                if (isSelected) {
                  selectedValues.delete(option.value)
                } else {
                  selectedValues.add(option.value)
                }
                const filterValues = Array.from(selectedValues)
                column?.setFilterValue(
                  filterValues.length ? filterValues : undefined,
                )
              }"
            >
              <div
                :class="[
                  'mr-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary',
                  selectedValues.has(option.value)
                    ? 'bg-primary text-primary-foreground'
                    : 'opacity-50 [&_svg]:invisible',
                ]"
              >
                <Icon name="lucide:check" class="w-4 h-4" />
              </div>
              <Icon v-if="option.icon" :name="option.icon" class="w-4 h-4 mr-2 text-muted-foreground" />
              <span>{{ option.label }}</span>
              <span
                v-if="facets?.get(option.value)"
                class="flex items-center justify-center w-4 h-4 ml-auto font-mono text-xs"
              >
                {{ facets.get(option.value) }}
              </span>
            </CommandItem>
          </CommandGroup>
          <template v-if="selectedValues.size > 0">
            <CommandSeparator />
            <CommandGroup>
              <CommandItem
                :value="'clear-filters'"
                class="justify-center text-center"
                @select="column?.setFilterValue(undefined)"
              >
                Clear filters
              </CommandItem>
            </CommandGroup>
          </template>
        </CommandList>
      </Command>
    </PopoverContent>
  </Popover>
</template>
import type { ColumnDef } from '@tanstack/vue-table'
import type { Alert } from '~/composables/useAlerts'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { h } from 'vue'
import DataTableColumnHeader from '@/components/DataTableColumnHeader.vue'

export const severityOptions = [
  {
    value: 'high',
    label: 'High',
    icon: 'lucide:alert-triangle',
  },
  {
    value: 'medium',
    label: 'Medium',
    icon: 'lucide:alert-circle',
  },
  {
    value: 'low',
    label: 'Low',
    icon: 'lucide:info',
  },
]

export const columns: ColumnDef<Alert>[] = [
  {
    id: 'select',
    header: ({ table }) => h(Checkbox, {
      'checked': table.getIsAllPageRowsSelected() || (table.getIsSomePageRowsSelected() ? 'indeterminate' : false),
      'onUpdate:checked': value => table.toggleAllPageRowsSelected(!!value),
      'ariaLabel': 'Select all',
      'class': 'translate-y-0.5',
    }),
    cell: ({ row }) => h(Checkbox, {
      'checked': row.getIsSelected(),
      'onUpdate:checked': value => row.toggleSelected(!!value),
      'ariaLabel': 'Select row',
      'class': 'translate-y-0.5',
    }),
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: 'alert_id',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'ID' }),
    cell: ({ row }) => h('div', { class: 'w-[80px] font-medium' }, row.getValue('alert_id')),
    enableHiding: false,
  },
  {
    accessorKey: 'severity',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Severity' }),
    cell: ({ row }) => {
      const severity = severityOptions.find(
        status => status.value === row.getValue('severity'),
      )
      if (!severity) return null
      return h('div', { class: 'flex items-center' }, [
        h('div', { class: 'flex items-center gap-2' }, [
          h(Badge, {
            variant: severity.value === 'high' ? 'destructive' : 'default',
            class: 'capitalize',
          }, () => [
            h('Icon', { name: severity.icon, class: 'w-3 h-3 mr-1' }),
            severity.label,
          ]),
        ]),
      ])
    },
    filterFn: (row, id, value) => {
      return value.includes(row.getValue(id))
    },
  },
  {
    accessorKey: 'detect_time',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Time' }),
    cell: ({ row }) => h('div', { class: 'w-[150px]' }, new Date(row.getValue('detect_time')).toLocaleString()),
  },
  {
    accessorKey: 'classification_text',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Classification' }),
    cell: ({ row }) => h('div', { class: 'max-w-[500px] truncate' }, row.getValue('classification_text')),
  },
  {
    accessorKey: 'source_ipv4',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Source' }),
    cell: ({ row }) => h('div', { class: 'w-[120px]' }, row.getValue('source_ipv4')),
  },
  {
    accessorKey: 'target_ipv4',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Target' }),
    cell: ({ row }) => h('div', { class: 'w-[120px]' }, row.getValue('target_ipv4')),
  },
  {
    accessorKey: 'analyzer.name',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Analyzer' }),
    cell: ({ row }) => h('div', { class: 'w-[150px]' }, row.original.analyzer.name),
  },
] 
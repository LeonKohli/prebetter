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
    header: ({ table }) => h('div', { class: 'w-[48px] flex items-center justify-center' }, [
      h(Checkbox, {
        'checked': table.getIsAllPageRowsSelected() || (table.getIsSomePageRowsSelected() ? 'indeterminate' : false),
        'onUpdate:checked': value => table.toggleAllPageRowsSelected(!!value),
        'aria-label': 'Select all',
        'class': 'translate-y-[2px]',
      }),
    ]),
    cell: ({ row }) => h('div', { class: 'w-[48px] flex items-center justify-center' }, [
      h(Checkbox, {
        'checked': row.getIsSelected(),
        'onUpdate:checked': value => row.toggleSelected(!!value),
        'aria-label': 'Select row',
        'class': 'translate-y-[2px]',
      }),
    ]),
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
    id: 'classification_text',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Classification' }),
    cell: ({ row }) => h('div', { class: 'max-w-[500px] truncate' }, row.getValue('classification_text')),
  },
  {
    accessorKey: 'source_ipv4',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Source IP' }),
    cell: ({ row }) => h('div', { class: 'w-[120px]' }, row.getValue('source_ipv4')),
  },
  {
    accessorKey: 'target_ipv4',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Target IP' }),
    cell: ({ row }) => h('div', { class: 'w-[120px]' }, row.getValue('target_ipv4')),
  },
  {
    accessorKey: 'analyzer.name',
    id: 'analyzer',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Analyzer' }),
    cell: ({ row }) => h('div', { class: 'w-[150px]' }, row.original.analyzer.name),
  },
] 
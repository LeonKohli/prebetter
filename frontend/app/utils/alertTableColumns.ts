import type { ColumnDef } from '@tanstack/vue-table'
import { h } from 'vue'
import { ArrowUpDown } from 'lucide-vue-next'
import type { AlertListItem, GroupedAlert, TimeInfo, AnalyzerInfo } from '@/types/alerts'
import AlertActions from '@/components/alerts/AlertActions.vue'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'

export const useAlertTableColumns = () => {
  const groupedColumns: ColumnDef<GroupedAlert>[] = [
    {
      accessorKey: 'source_ipv4',
      header: ({ column }) => {
        return h(Button, {
          variant: 'ghost',
          onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
          class: 'hover:bg-transparent px-0 font-semibold',
        }, () => ['Source IP', h(ArrowUpDown, { class: 'ml-2 h-3 w-3 text-muted-foreground' })])
      },
      cell: ({ row }) => row.getValue('source_ipv4') || 'Unknown',
    },
    {
      accessorKey: 'target_ipv4',
      header: ({ column }) => {
        return h(Button, {
          variant: 'ghost',
          onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
          class: 'hover:bg-transparent px-0 font-semibold',
        }, () => ['Target IP', h(ArrowUpDown, { class: 'ml-2 h-3 w-3 text-muted-foreground' })])
      },
      cell: ({ row }) => row.getValue('target_ipv4') || 'Unknown',
    },
    {
      accessorKey: 'total_count',
      header: ({ column }) => {
        return h(Button, {
          variant: 'ghost',
          onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
          class: 'hover:bg-transparent px-0 font-semibold',
        }, () => ['Count', h(ArrowUpDown, { class: 'ml-2 h-3 w-3 text-muted-foreground' })])
      },
      cell: ({ row }) => h('div', { class: 'font-semibold text-foreground' }, row.getValue('total_count')),
    },
    {
      id: 'actions',
      enableHiding: false,
      cell: ({ row }) => h(AlertActions, {
        alert: row.original,
        isGrouped: true,
      }),
    },
  ]

  const ungroupedColumns: ColumnDef<AlertListItem>[] = [
    {
      id: 'select',
      header: ({ table }) => h(Checkbox, {
        'modelValue': table.getIsAllPageRowsSelected() || (table.getIsSomePageRowsSelected() && 'indeterminate'),
        'onUpdate:modelValue': (value: boolean | 'indeterminate') => {
          if (typeof value === 'boolean') {
            table.toggleAllPageRowsSelected(value)
          }
        },
        'ariaLabel': 'Select all',
      }),
      cell: ({ row }) => h(Checkbox, {
        'modelValue': row.getIsSelected(),
        'onUpdate:modelValue': (value: boolean | 'indeterminate') => {
          if (typeof value === 'boolean') {
            row.toggleSelected(value)
          }
        },
        'ariaLabel': 'Select row',
      }),
      enableSorting: false,
      enableHiding: false,
    },
    {
      accessorKey: 'detected_at',
      header: ({ column }) => {
        return h(Button, {
          variant: 'ghost',
          onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
          class: 'hover:bg-transparent px-0 font-semibold',
        }, () => ['Time', h(ArrowUpDown, { class: 'ml-2 h-3 w-3 text-muted-foreground' })])
      },
      cell: ({ row }) => {
        const time = row.getValue<TimeInfo | string>('detected_at')
        const timestamp = time && typeof time === 'object' && 'timestamp' in time ? time.timestamp : time
        const date = timestamp ? new Date(timestamp) : new Date()
        return h('div', { class: 'text-sm' }, [
          h('div', { class: 'font-medium' }, date.toLocaleDateString()),
          h('div', { class: 'text-xs text-muted-foreground' }, date.toLocaleTimeString())
        ])
      },
    },
    {
      accessorKey: 'severity',
      header: ({ column }) => {
        return h(Button, {
          variant: 'ghost',
          onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
          class: 'hover:bg-transparent px-0 font-semibold',
        }, () => ['Severity', h(ArrowUpDown, { class: 'ml-2 h-3 w-3 text-muted-foreground' })])
      },
      cell: ({ row }) => {
        const severity = row.getValue('severity') as string
        const severityLower = severity?.toLowerCase()
        
        const severityClasses: Record<string, string> = {
          high: 'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-primary text-primary-foreground',
          medium: 'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-accent text-accent-foreground',
          low: 'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-muted text-muted-foreground',
        }
        
        return h('span', { 
          class: severityClasses[severityLower] || severityClasses.low
        }, severity?.toUpperCase() || 'UNKNOWN')
      },
    },
    {
      accessorKey: 'classification_text',
      header: ({ column }) => {
        return h(Button, {
          variant: 'ghost',
          onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
          class: 'hover:bg-transparent px-0 font-semibold',
        }, () => ['Classification', h(ArrowUpDown, { class: 'ml-2 h-3 w-3 text-muted-foreground' })])
      },
      cell: ({ row }) => row.getValue('classification_text') || 'Unknown',
    },
    {
      accessorKey: 'source_ipv4',
      header: ({ column }) => {
        return h(Button, {
          variant: 'ghost',
          onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
          class: 'hover:bg-transparent px-0 font-semibold',
        }, () => ['Source IP', h(ArrowUpDown, { class: 'ml-2 h-3 w-3 text-muted-foreground' })])
      },
      cell: ({ row }) => row.getValue('source_ipv4') || 'Unknown',
    },
    {
      accessorKey: 'target_ipv4',
      header: ({ column }) => {
        return h(Button, {
          variant: 'ghost',
          onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
          class: 'hover:bg-transparent px-0 font-semibold',
        }, () => ['Target IP', h(ArrowUpDown, { class: 'ml-2 h-3 w-3 text-muted-foreground' })])
      },
      cell: ({ row }) => row.getValue('target_ipv4') || 'Unknown',
    },
    {
      accessorKey: 'analyzer',
      header: ({ column }) => {
        return h(Button, {
          variant: 'ghost',
          onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
          class: 'hover:bg-transparent px-0 font-semibold',
        }, () => ['Analyzer', h(ArrowUpDown, { class: 'ml-2 h-3 w-3 text-muted-foreground' })])
      },
      cell: ({ row }) => {
        const analyzer = row.getValue<AnalyzerInfo | undefined>('analyzer')
        return analyzer?.name || 'Unknown'
      },
    },
    {
      id: 'actions',
      enableHiding: false,
      cell: ({ row }) => h(AlertActions, {
        alert: row.original,
        isGrouped: false,
      }),
    },
  ]

  const sortFieldMap = {
    'detected_at': 'detect_time',
    'created_at': 'create_time',
    'source_ipv4': 'source_ip',
    'target_ipv4': 'target_ip',
    'classification_text': 'classification',
    'analyzer': 'analyzer',
    'severity': 'severity',
    'total_count': 'alert_id',
  } as const satisfies Record<string, string>

  const filterFieldMap = {
    'classification_text': 'classification',
    'source_ipv4': 'source_ip',
    'target_ipv4': 'target_ip',
    'start_date': 'start_date',
    'end_date': 'end_date',
  } as const satisfies Record<string, string>

  return {
    groupedColumns,
    ungroupedColumns,
    sortFieldMap,
    filterFieldMap,
  }
}
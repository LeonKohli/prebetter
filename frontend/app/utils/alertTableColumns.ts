import type { ColumnDef, Column } from '@tanstack/vue-table'
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-vue-next'
import type { AlertListItem, GroupedAlert, GroupedAlertDetail, TimeInfo, AnalyzerInfo } from '@/types/alerts'
import AlertActions from '@/components/alerts/AlertActions.vue'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'

export const useAlertTableColumns = () => {
  // Helper to create sortable header with proper indicators
  // Using computed-like pattern for better reactivity as per Vue best practices
  const createSortableHeader = <TData,>(label: string) => ({ column }: { column: Column<TData> }) => {
    // Use computed-like derivation for reactive state
    const sortState = column.getIsSorted()
    const isActive = sortState !== false
    const isAscending = sortState === 'asc'
    const isDescending = sortState === 'desc'
    
    // Determine which icon to show based on state
    const SortIcon = isAscending 
      ? ArrowUp 
      : isDescending 
        ? ArrowDown 
        : ArrowUpDown
    
    // Computed styling based on sort state
    const iconClass = isActive 
      ? 'ml-2 h-3.5 w-3.5 text-foreground transition-all' // Active: larger and primary color
      : 'ml-2 h-3 w-3 text-muted-foreground opacity-60 transition-all' // Inactive: smaller and muted
    
    const buttonClass = isActive
      ? 'hover:bg-transparent px-0 font-semibold text-foreground' // Active column
      : 'hover:bg-transparent px-0 font-semibold text-muted-foreground' // Inactive column
    
    // Return VNode with proper event handler
    return h(Button, {
      variant: 'ghost',
      onClick: () => column.toggleSorting(isAscending),
      class: buttonClass,
      'aria-label': `Sort by ${label} ${isAscending ? 'descending' : 'ascending'}`,
      'aria-sort': isAscending ? 'ascending' : isDescending ? 'descending' : 'none'
    }, () => [label, h(SortIcon, { class: iconClass })])
  }

  const groupedColumns: ColumnDef<GroupedAlert>[] = [
    {
      accessorKey: 'total_count',
      header: createSortableHeader('Count'),
      cell: ({ row }) => h('div', { class: 'font-semibold text-foreground text-lg' }, row.getValue<number>('total_count').toString()),
    },
    {
      accessorKey: 'source_ipv4',
      header: createSortableHeader('Source IP'),
      cell: ({ row }) => h('span', { class: 'font-mono text-sm' }, row.getValue('source_ipv4') || 'Unknown'),
    },
    {
      accessorKey: 'target_ipv4',
      header: createSortableHeader('Target IP'),
      cell: ({ row }) => h('span', { class: 'font-mono text-sm' }, row.getValue('target_ipv4') || 'Unknown'),
    },
    {
      id: 'details',
      accessorKey: 'alerts',
      header: 'Alert Details',
      cell: ({ row }) => {
        const alerts = row.original.alerts
        const totalCount = row.original.total_count
        
        if (!alerts || alerts.length === 0) {
          return h('div', { class: 'text-muted-foreground' }, 'No classification data available')
        }
        
        // Sort alerts by count descending
        const sortedAlerts = [...alerts].sort((a, b) => b.count - a.count)
        
        // Create a grid/table-like display for the alert details
        return h('div', { class: 'space-y-2 py-1' }, 
          sortedAlerts.map(alert => {
            const date = alert.detected_at ? new Date(alert.detected_at) : null
            const dateStr = date ? date.toLocaleDateString('de-DE', {
              day: '2-digit',
              month: '2-digit',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
              hour12: false // Ensure 24-hour format
            }) : 'Unknown'
            
            const analyzers = alert.analyzer || []
            const analyzerStr = analyzers.length === 0 ? 'Unknown' : 
                               analyzers.length === 1 ? analyzers[0] :
                               analyzers.length <= 3 ? analyzers.join(', ') :
                               `${analyzers[0]}, ${analyzers[1]} +${analyzers.length - 2} more`
            
            return h('div', { 
              class: 'grid grid-cols-[auto_1fr_auto] gap-4 items-center p-2 rounded hover:bg-muted/50 transition-colors',
              key: alert.classification 
            }, [
              // Count
              h('div', { class: 'flex items-center gap-2' }, [
                h('span', { class: 'font-semibold text-base min-w-[3rem] text-right' }, alert.count.toString()),
                h('span', { class: 'text-muted-foreground' }, '×')
              ]),
              // Classification & Analyzer
              h('div', { class: 'space-y-1' }, [
                h('div', { class: 'font-medium' }, alert.classification),
                h('div', { class: 'text-xs text-muted-foreground' }, `Analyzer: ${analyzerStr}`)
              ]),
              // Date
              h('div', { class: 'text-xs text-muted-foreground text-right' }, dateStr)
            ])
          })
        )
      },
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
      header: createSortableHeader('Time'),
      cell: ({ row }) => {
        const time = row.getValue<TimeInfo | string>('detected_at')
        const timestamp = time && typeof time === 'object' && 'timestamp' in time ? time.timestamp : time
        const date = timestamp ? new Date(timestamp) : new Date()
        const timeAgo = useTimeAgo(date)
        
        return h('div', { class: 'text-sm' }, [
          h('div', { class: 'font-medium' }, date.toLocaleDateString('de-DE', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
          })),
          h('div', { class: 'text-xs text-muted-foreground flex items-center gap-1' }, [
            h('span', {}, date.toLocaleTimeString('de-DE', {
              hour: '2-digit',
              minute: '2-digit',
              hour12: false
            })),
            h('span', { class: 'text-muted-foreground/70' }, '•'),
            h('span', { class: 'text-muted-foreground/70' }, timeAgo.value)
          ])
        ])
      },
    },
    {
      accessorKey: 'severity',
      header: createSortableHeader('Severity'),
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
      header: createSortableHeader('Classification'),
      cell: ({ row }) => row.getValue('classification_text') || 'Unknown',
    },
    {
      accessorKey: 'source_ipv4',
      header: createSortableHeader('Source IP'),
      cell: ({ row }) => row.getValue('source_ipv4') || 'Unknown',
    },
    {
      accessorKey: 'target_ipv4',
      header: createSortableHeader('Target IP'),
      cell: ({ row }) => row.getValue('target_ipv4') || 'Unknown',
    },
    {
      accessorKey: 'analyzer',
      header: createSortableHeader('Analyzer'),
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
    'total_count': 'total_count', // Backend now supports this!
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
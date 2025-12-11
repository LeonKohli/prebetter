import type { ColumnDef, RowData } from "@tanstack/vue-table";
import {
  AlertsActions,
  AlertsClassificationBadges,
  AlertsDataTableColumnHeader,
  Checkbox,
  TimeAgo,
} from "#components";

// Extend TanStack Table's TableMeta interface for type-safe meta access
declare module "@tanstack/vue-table" {
  interface TableMeta<TData extends RowData> {
    onViewDetails?: (alertId: string) => void;
    onRequestDeleteSingle?: (alert: AlertListItem) => void;
    onRequestDeleteGroup?: (group: CompactGroupedAlert | FlattenedGroupedAlert) => void;
  }
}

export const useAlertTableColumns = () => {
  // New compact grouped columns - one group per row
  const compactGroupedColumns: ColumnDef<CompactGroupedAlert>[] = [
    {
      accessorKey: "total_count",
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Alerts" }),
      cell: ({ row }) => {
        const totalCount = row.getValue("total_count") as number;
        const classificationCount = row.original.alerts?.length || 0;

        return h("div", { class: "flex flex-col" }, [
          h(
            "span",
            { class: "font-bold text-lg text-foreground" },
            totalCount.toString(),
          ),
          h(
            "span",
            { class: "text-xs text-muted-foreground" },
            `${classificationCount} type${classificationCount !== 1 ? "s" : ""}`,
          ),
        ]);
      },
      size: 100,
    },
    {
      accessorKey: "source_ipv4",
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Source IP" }),
      cell: ({ row }) =>
        h(
          "span",
          { class: "font-mono text-sm" },
          row.getValue("source_ipv4") || "Unknown",
        ),
      size: 150,
    },
    {
      accessorKey: "target_ipv4",
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Target IP" }),
      cell: ({ row }) =>
        h(
          "span",
          { class: "font-mono text-sm" },
          row.getValue("target_ipv4") || "Unknown",
        ),
      size: 150,
    },
    {
      accessorKey: "alerts",
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Classifications" }),
      cell: ({ row }) => {
        const alerts = row.original.alerts || [];
        return h(AlertsClassificationBadges, {
          classifications: alerts,
          sourceIp: row.original.source_ipv4 || "",
          targetIp: row.original.target_ipv4 || "",
          maxVisible: 5,
        });
      },
      enableSorting: false,
    },
    {
      id: "detected_at",
      accessorFn: (row) => row.alerts?.[0]?.detected_at,
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Last Detected" }),
      cell: ({ row }) => {
        const dateStr = row.original.alerts?.[0]?.detected_at;

        if (!dateStr)
          return h("span", { class: "text-muted-foreground" }, "Unknown");

        return h("div", { class: "text-sm" }, [
          h("div", { class: "font-medium" }, formatTimestampCompact(dateStr)),
          h("div", { class: "text-xs text-muted-foreground" }, [
            h(TimeAgo, { time: dateStr }),
          ]),
        ]);
      },
      size: 140,
    },
    {
      id: "actions",
      enableHiding: false,
      cell: ({ row, table }) =>
        h(AlertsActions, {
          alert: row.original,
          isGrouped: true,
          onViewDetails: table.options.meta?.onViewDetails,
          onRequestDeleteGroup: table.options.meta?.onRequestDeleteGroup,
        }),
      size: 60,
    },
  ];

  const ungroupedColumns: ColumnDef<AlertListItem>[] = [
    {
      id: "select",
      header: ({ table }) =>
        h(Checkbox, {
          modelValue:
            table.getIsAllPageRowsSelected() ||
            (table.getIsSomePageRowsSelected() && "indeterminate"),
          "onUpdate:modelValue": (value: boolean | "indeterminate") => {
            if (typeof value === "boolean") {
              table.toggleAllPageRowsSelected(value);
            }
          },
          ariaLabel: "Select all",
        }),
      cell: ({ row }) =>
        h(Checkbox, {
          modelValue: row.getIsSelected(),
          "onUpdate:modelValue": (value: boolean | "indeterminate") => {
            if (typeof value === "boolean") {
              row.toggleSelected(value);
            }
          },
          ariaLabel: "Select row",
        }),
      enableSorting: false,
      enableHiding: false,
    },
    {
      accessorKey: "detected_at",
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Time" }),
      cell: ({ row }) => {
        const time = row.getValue<TimeInfo | string>("detected_at");
        const timestamp =
          time && typeof time === "object" && "timestamp" in time
            ? time.timestamp
            : time;

        if (!timestamp)
          return h("span", { class: "text-muted-foreground" }, "Unknown");

        return h("div", { class: "text-sm" }, [
          h("div", { class: "font-medium" }, formatTimestampCompact(timestamp)),
          h("div", { class: "text-xs text-muted-foreground" }, [
            h(TimeAgo, { time: timestamp }),
          ]),
        ]);
      },
    },
    {
      accessorKey: "severity",
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Severity" }),
      cell: ({ row }) => {
        const severity = row.getValue("severity") as string;
        const severityLower = severity?.toLowerCase();
        const severityClasses: Record<string, string> = {
          high: "inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-primary text-primary-foreground",
          medium: "inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-accent text-accent-foreground",
          low: "inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-muted text-muted-foreground",
        };
        return h(
          "span",
          { class: severityClasses[severityLower] || severityClasses.low },
          severity?.toUpperCase() || "UNKNOWN",
        );
      },
    },
    {
      accessorKey: "classification_text",
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Classification" }),
      cell: ({ row }) => {
        const classification = row.getValue("classification_text") || "Unknown";
        const correlationDesc = row.original.correlation_description;

        if (correlationDesc) {
          return h(
            "div",
            { class: "flex items-center gap-1.5", title: correlationDesc },
            [
              h(
                "span",
                { class: "text-blue-600 dark:text-blue-400 text-xs" },
                "●",
              ),
              String(classification),
            ],
          );
        }
        return String(classification);
      },
    },
    {
      accessorKey: "source_ipv4",
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Source IP" }),
      cell: ({ row }) => row.getValue("source_ipv4") || "Unknown",
    },
    {
      accessorKey: "target_ipv4",
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Target IP" }),
      cell: ({ row }) => row.getValue("target_ipv4") || "Unknown",
    },
    {
      accessorKey: "analyzer",
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Analyzer" }),
      cell: ({ row }) => {
        const analyzer = row.getValue<AnalyzerInfo | undefined>("analyzer");
        return analyzer?.name || "Unknown";
      },
    },
    {
      id: "actions",
      enableHiding: false,
      cell: ({ row, table }) =>
        h(AlertsActions, {
          alert: row.original,
          isGrouped: false,
          onViewDetails: table.options.meta?.onViewDetails,
          onRequestDeleteSingle: table.options.meta?.onRequestDeleteSingle,
        }),
    },
  ];

  const sortFieldMap = {
    detected_at: "detect_time",
    created_at: "create_time",
    source_ipv4: "source_ip",
    target_ipv4: "target_ip",
    classification_text: "classification",
    analyzer: "analyzer",
    severity: "severity",
    total_count: "total_count", // Backend now supports this!
    count: "total_count", // Map count to total_count for backward compat
    alert_count: "total_count", // Map alert_count to total_count for compact view
  } as const satisfies Record<string, string>;

  const filterFieldMap = {
    classification_text: "classification",
    source_ipv4: "source_ip",
    target_ipv4: "target_ip",
    start_date: "start_date",
    end_date: "end_date",
    date_preset: "date_preset",
    severity: "severity",
    server: "server",
  } as const satisfies Record<string, string>;

  return {
    compactGroupedColumns,
    ungroupedColumns,
    sortFieldMap,
    filterFieldMap,
  };
};

import type { ColumnDef, RowData } from "@tanstack/vue-table";
import {
  AlertsActions,
  AlertsClassificationBadges,
  AlertsDataTableColumnHeader,
  TimeAgo,
} from "#components";

// Extend TanStack Table's TableMeta interface for type-safe meta access
declare module "@tanstack/vue-table" {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars -- Declaration merging requires TanStack's type parameter name.
  interface TableMeta<TData extends RowData> {
    onViewDetails?: (alertId: string) => void;
  }
}

export const useAlertTableColumns = () => {
  // New compact grouped columns - one group per row
  const compactGroupedColumns: ColumnDef<GroupedAlert>[] = [
    {
      accessorKey: "total_count",
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Alerts" }),
      cell: ({ row }) => {
        const totalCount = row.original.total_count;
        const classificationCount = row.original.alerts.length;

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
        const alerts = row.original.alerts;
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
      accessorFn: (row) => row.alerts[0]?.detected_at,
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Last Detected" }),
      cell: ({ row }) => {
        const dateStr = row.original.alerts[0]?.detected_at;

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
        }),
      size: 60,
    },
  ];

  const ungroupedColumns: ColumnDef<AlertListItem>[] = [
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
        const severity = row.original.severity;
        const severityLower = severity?.toLowerCase();
        const severityClasses: Record<string, string> = {
          high: "inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-primary text-primary-foreground",
          medium: "inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-accent text-accent-foreground",
          low: "inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-muted text-muted-foreground",
        };
        return h(
          "span",
          { class: (severityLower && severityClasses[severityLower]) || severityClasses.low },
          severity?.toUpperCase() || "UNKNOWN",
        );
      },
    },
    {
      accessorKey: "classification_text",
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Classification" }),
      cell: ({ row }) => {
        return row.original.classification_text || "Unknown";
      },
    },
    {
      accessorKey: "source_ipv4",
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Source IP" }),
      cell: ({ row }) => row.original.source_ipv4 || "Unknown",
    },
    {
      accessorKey: "target_ipv4",
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Target IP" }),
      cell: ({ row }) => row.original.target_ipv4 || "Unknown",
    },
    {
      accessorKey: "analyzer",
      header: ({ column }) =>
        h(AlertsDataTableColumnHeader, { column, title: "Sensor" }),
      cell: ({ row }) => {
        return row.original.analyzer?.name || "Unknown";
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
        }),
    },
  ];

  const sortFieldMap = {
    detected_at: "detect_time",
    source_ipv4: "source_ip",
    target_ipv4: "target_ip",
    classification_text: "classification",
    analyzer: "analyzer",
    severity: "severity",
    total_count: "total_count",
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

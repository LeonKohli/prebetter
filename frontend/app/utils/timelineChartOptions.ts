import type { ApexOptions } from 'apexcharts'
import type { TimeFrame } from '../../shared/types/timeline'
import { formatDayLandmark, formatTimelineBucketTitle, getDayBoundaries, getTimelineTickFormat, pickClippedLabels, type TimelineBar, type TimelineModel } from './timelineChart'

type ChartEvents = NonNullable<NonNullable<ApexOptions['chart']>['events']>

export interface TimelineChartInput {
  model: TimelineModel
  frame: TimeFrame
  /** Bar colour (hex). */
  color: string
  mode: 'light' | 'dark'
  /** The selected window, for the tooltip title of partial buckets. */
  window: { start: number, end: number }
  onZoomed?: ChartEvents['zoomed']
  onBarClick?: ChartEvents['dataPointSelection']
}

const formatCount = (count: number) => count.toLocaleString('en-GB')
const formatCompact = (count: number) => new Intl.NumberFormat('en-GB', { notation: 'compact', maximumFractionDigits: 1 }).format(count)

/** One series; a bucket that is still filling is drawn lighter. */
export function createTimelineSeries(model: TimelineModel, color: string) {
  return [{
    name: 'Alerts',
    data: model.bars.map((bar: TimelineBar) => ({
      x: bar.x,
      y: bar.plotY,
      ...(bar.running && { fillColor: `${color}80` }),
    })),
  }]
}

/**
 * Apex options for the alert timeline. Only what differs from the global defaults in
 * plugins/apexcharts.client.ts. The chart height is set by the component (height prop and the
 * responsive breakpoint).
 */
export function createTimelineOptions(input: TimelineChartInput): ApexOptions {
  const { model, frame, color, mode, window, onZoomed, onBarClick } = input
  const bars = model.bars
  const tickFormat = getTimelineTickFormat(frame, model.xRange.max - model.xRange.min)

  return {
    chart: {
      id: 'alerts-timeline',
      background: 'transparent',
      animations: { enabled: true, easing: 'easeout', dynamicAnimation: { enabled: true, speed: 300 } },
      zoom: { enabled: true, type: 'x', autoScaleYaxis: true, allowMouseWheelZoom: false },
      events: { zoomed: onZoomed, dataPointSelection: onBarClick },
    },
    plotOptions: { bar: { borderRadius: 3, columnWidth: '80%' } },
    xaxis: {
      type: 'datetime',
      min: model.xRange.min,
      max: model.xRange.max,
      // One label per bar while they fit (n bars span n - 1 tick intervals); Apex picks the ticks
      // for more. 'dataPoints' is ignored on a datetime axis in Apex 8.
      tickAmount: bars.length >= 2 && bars.length <= 30 ? bars.length - 1 : undefined,
      labels: {
        datetimeUTC: false,
        format: tickFormat,
        // Short labels never need the default -45 degrees. Apex reserves the rotated height in
        // its first layout pass and draws the hover column with that smaller grid.
        rotate: 0,
        hideOverlappingLabels: true,
        style: { fontSize: '11px' },
      },
      crosshairs: { width: 'barWidth', fill: { type: 'solid', color: 'var(--color-muted)' }, opacity: 0.3 },
    },
    yaxis: {
      min: 0,
      max: model.yMax,
      labels: { formatter: (value: number) => Math.round(value).toString() },
    },
    tooltip: {
      theme: mode,
      shared: true,
      intersect: false,
      // apexcharts 5.13+ defaults tooltip.arrow to true; keep the flush look
      arrow: false,
      x: { formatter: (_value, opts) => {
        const bar = opts ? bars[opts.dataPointIndex] : undefined
        return bar ? formatTimelineBucketTitle(bar, frame, window) : ''
      } },
      // The drawn height can differ from the count (outlier cap, minimum height): show the count.
      y: { formatter: (_value: number, opts?: { dataPointIndex: number }) => {
        const count = opts ? bars[opts.dataPointIndex]?.y ?? 0 : 0
        return `${formatCount(count)} alert${count !== 1 ? 's' : ''}`
      } },
    },
    annotations: {
      // Day landmarks for clock-time labels: a line at each local midnight, named with its date.
      xaxis: tickFormat !== 'HH:mm'
        ? []
        : getDayBoundaries(model.xRange.min, model.xRange.max).map(x => ({
            x,
            borderColor: mode === 'dark' ? '#525252' : '#a3a3a3',
            strokeDashArray: 3,
            label: {
              text: formatDayLandmark(x),
              orientation: 'horizontal' as const,
              borderColor: 'transparent',
              offsetX: 4,
              textAnchor: 'start',
              style: { color: mode === 'dark' ? '#a3a3a3' : '#737373', background: 'transparent', fontSize: '10px', fontWeight: 600 },
            },
          })),
      // Bars above a capped axis run off the top; the label says how far.
      points: model.yMax === undefined
        ? []
        : pickClippedLabels(bars).map(bar => ({
            x: bar.x,
            y: model.yMax,
            marker: { size: 0 },
            label: {
              text: `▲ ${formatCompact(bar.y)}`,
              borderColor: 'transparent',
              offsetY: -2,
              style: { color: '#ffffff', background: mode === 'dark' ? '#b91c1c' : '#991b1b', fontSize: '10px', padding: { left: 4, right: 4, top: 1, bottom: 1 } },
            },
          })),
    },
    colors: [color],
    // Phones get a lower chart and no drag-zoom.
    responsive: [{ breakpoint: 768, options: { chart: { height: 140, zoom: { enabled: false } } } }],
  }
}

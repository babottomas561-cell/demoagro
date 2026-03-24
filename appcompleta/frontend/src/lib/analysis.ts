export interface NumericPoint {
  label: string
  value: number
}

export interface ProjectionPoint extends NumericPoint {
  projected?: boolean
}

export interface DeviationResult {
  actual: number
  expected: number
  delta: number
  deltaPct: number
}

export interface AnomalyPoint extends NumericPoint {
  zScore: number
}

function mean(values: number[]) {
  if (!values.length) return 0
  return values.reduce((acc, value) => acc + value, 0) / values.length
}

function stdDev(values: number[]) {
  if (values.length <= 1) return 0
  const avg = mean(values)
  const variance =
    values.reduce((acc, value) => acc + (value - avg) ** 2, 0) / values.length
  return Math.sqrt(variance)
}

function nextLabel(label: string, offset: number) {
  if (/^\d{4}-\d{2}$/.test(label)) {
    const [yearRaw, monthRaw] = label.split('-').map(Number)
    const date = new Date(yearRaw, monthRaw - 1 + offset, 1)
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
  }
  return `Proy ${offset}`
}

export function linearProjection(
  points: NumericPoint[],
  horizon = 3
): ProjectionPoint[] {
  if (!points.length) return []
  if (points.length === 1) {
    return [
      ...points,
      ...Array.from({ length: horizon }, (_, index) => ({
        label: nextLabel(points[0].label, index + 1),
        value: points[0].value,
        projected: true,
      })),
    ]
  }

  const xs = points.map((_, index) => index + 1)
  const ys = points.map((point) => point.value)
  const xAvg = mean(xs)
  const yAvg = mean(ys)
  const numerator = xs.reduce(
    (acc, x, index) => acc + (x - xAvg) * (ys[index] - yAvg),
    0
  )
  const denominator = xs.reduce((acc, x) => acc + (x - xAvg) ** 2, 0) || 1
  const slope = numerator / denominator
  const intercept = yAvg - slope * xAvg

  const projected = Array.from({ length: horizon }, (_, index) => {
    const x = points.length + index + 1
    return {
      label: nextLabel(points[points.length - 1].label, index + 1),
      value: Number((intercept + slope * x).toFixed(2)),
      projected: true,
    }
  })

  return [...points, ...projected]
}

export function movingAverageProjection(
  points: NumericPoint[],
  horizon = 3,
  window = 3
): ProjectionPoint[] {
  if (!points.length) return []
  const seed = [...points]
  const projected: ProjectionPoint[] = []

  for (let index = 0; index < horizon; index += 1) {
    const base = [...seed, ...projected]
    const trailing = base.slice(-window)
    const nextValue = mean(trailing.map((item) => item.value))
    projected.push({
      label: nextLabel(points[points.length - 1].label, index + 1),
      value: Number(nextValue.toFixed(2)),
      projected: true,
    })
  }

  return [...points, ...projected]
}

export function computeDeviation(actual: number, expected: number): DeviationResult {
  const delta = actual - expected
  const deltaPct = expected ? (delta / expected) * 100 : 0
  return {
    actual,
    expected,
    delta: Number(delta.toFixed(2)),
    deltaPct: Number(deltaPct.toFixed(2)),
  }
}

export function detectAnomalies(
  points: NumericPoint[],
  zThreshold = 1.2
): AnomalyPoint[] {
  if (points.length < 3) return []
  const values = points.map((point) => point.value)
  const avg = mean(values)
  const deviation = stdDev(values)
  if (!deviation) return []

  return points
    .map((point) => ({
      ...point,
      zScore: Number(((point.value - avg) / deviation).toFixed(2)),
    }))
    .filter((point) => Math.abs(point.zScore) >= zThreshold)
    .sort((a, b) => Math.abs(b.zScore) - Math.abs(a.zScore))
}

export function buildSensitivityScenarios(
  baseline: number,
  shocks: number[]
): NumericPoint[] {
  return shocks.map((shock) => ({
    label: `${shock > 0 ? '+' : ''}${Math.round(shock * 100)}%`,
    value: Number((baseline * (1 + shock)).toFixed(2)),
  }))
}


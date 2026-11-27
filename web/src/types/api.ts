export type Severity = "low" | "medium" | "high";
export type MetricKind = "sales" | "profit";
export type TargetField =
  | "order_date"
  | "sales"
  | "profit"
  | "product"
  | "category"
  | "region"
  | "quantity"
  | "discount_pct";

export interface UserProfile {
  id: number;
  name: string;
  email: string;
  job_title: string;
  company: string;
  location: string;
  bio: string;
  created_at: string;
  has_avatar: boolean;
  avatar_v: number;
}

export interface Badge {
  id: string;
  icon: string;
  name: string;
  how: string;
  earned: boolean;
}

export interface GamifyStats {
  xp: number;
  level: number;
  title: string;
  xp_into_level: number;
  xp_per_level: number;
  counts: Record<string, number>;
  badges: Badge[];
}

export interface SessionResponse {
  csrf_token: string;
  authenticated: boolean;
  user: UserProfile | null;
  stats: GamifyStats | null;
}

export interface AuthActionResponse {
  ok: boolean;
  next: string;
  csrf_token: string;
  user: UserProfile;
}

export interface QualityIssue {
  type: string;
  count: number;
  detail: string;
  severity: Severity;
}

export interface QualityReport {
  rows_in: number;
  rows_out: number;
  rows_removed: number;
  quality_score: number;
  date_range: [string, string] | [];
  issues: QualityIssue[];
}

export interface DatasetMeta {
  id: string;
  owner: number;
  filename: string;
  upload_date: string;
  row_count: number;
  quality: QualityReport;
}

export interface UploadSuccessResponse {
  dataset: DatasetMeta;
  months: string[];
  source_note: string;
}

export interface UploadNeedsMappingError {
  error: string;
  needs_mapping: true;
  token: string;
  filename: string;
  columns: string[];
  preview: Record<string, string>[];
  suggestions: Record<TargetField, string | null>;
  source_note: string;
}

export interface FilterOptions {
  regions: string[];
  categories: string[];
  products: string[];
  months: string[];
  min_date: string;
  max_date: string;
}

export interface DashboardKPIs {
  total_sales: number;
  total_profit: number;
  profit_margin: number | null;
  total_orders: number;
  units_sold: number;
  avg_order_value: number | null;
}

export interface MonthlyRow {
  month: string;
  sales: number;
  profit: number;
  orders: number;
  days: number;
  margin: number;
  sales_change: number | null;
  profit_change: number | null;
}

export interface GroupRow {
  name: string;
  sales: number;
  profit: number;
  orders: number;
  margin: number;
}

export interface DailyRow {
  date: string;
  sales: number;
  profit: number;
  orders: number;
}

export interface DashboardResponse {
  meta: DatasetMeta;
  options: FilterOptions;
  filtered_rows: number;
  kpis: DashboardKPIs;
  monthly: MonthlyRow[];
  products: GroupRow[];
  categories: GroupRow[];
  regions: GroupRow[];
  daily: DailyRow[];
  heatmap: { regions: string[]; products: string[]; z: number[][] };
  discount_bands: { band: string; sales: number; profit: number; orders: number; margin: number }[] | null;
  forecast: {
    next_month: string;
    history_months: number;
    sales: { projected: number; trend_per_month: number; band: number | null };
    profit: { projected: number; trend_per_month: number; band: number | null };
  } | null;
  pulse: { icon: string; label: string; value: string; detail: string }[];
  health: {
    score: number;
    grade: "Strong" | "Healthy" | "Watch closely" | "At risk";
    parts: { name: string; points: number; max: number; detail: string }[];
  };
}

export interface ContributorRow {
  name: string;
  previous: number;
  current: number;
  delta: number;
  pct: number | null;
  share_of_change: number;
}

export interface DriverChange {
  driver: "orders" | "units" | "avg_selling_price" | "margin" | "avg_discount";
  label: string;
  previous: number;
  current: number;
  change: number;
  unit: "%" | "pts";
}

export interface AnomalyItem {
  date: string;
  sales: number;
  profit: number;
  orders: number;
  typical_daily_sales: number;
  direction: "spike" | "dip";
  score: number;
  methods: string[];
  note: string;
}

export interface InvestigationResponse {
  question: string;
  investigation: {
    metric: MetricKind;
    comparison: {
      metric: MetricKind;
      previous_period: string;
      current_period: string;
      previous: number;
      current: number;
      delta: number;
      pct: number | null;
      direction: "decline" | "increase" | "flat";
      partial_warning: string | null;
    };
    severity: Severity;
    contributors: Record<"category" | "product" | "region" | "segment", ContributorRow[]>;
    drivers: { segment: string; changes: DriverChange[] } | null;
    kpi_changes: Record<"sales" | "profit" | "orders", { previous: number; current: number; pct: number | null }>;
    anomalies: AnomalyItem[];
    monthly_shifts: { month: string; metric: string; change_pct: number }[];
  };
  findings: { finding: string; evidence: string; severity: Severity }[];
  next_checks: string[];
  explanation: { text: string; source: "rules" | "llm"; llm_error?: string };
}

export interface WhatIfSegment {
  name: string;
  orders: number;
  sales: number;
  profit: number;
  prev_orders: number;
}

export interface WhatIfResponse {
  month: string;
  segment: string;
  baseline: { orders: number; sales: number; profit: number; margin: number; month_total_profit: number };
  previous_orders: number;
  restore_order_change_pct: number | null;
  inputs: { order_change_pct: number; price_change_pct: number; margin_change_pts: number };
  scenario: { orders: number; sales: number; profit: number; margin: number };
  delta_sales: number;
  delta_profit: number;
  pct_of_month_profit: number | null;
}

export interface GoalItem {
  metric: MetricKind;
  target: number;
  actual: number;
  pct: number;
  remaining: number;
  days_left: number;
  needed_per_day: number | null;
}

export interface NoteItem {
  id: number;
  text: string;
  created_at: string;
}

export interface PreviewResponse {
  rows: {
    order_date: string;
    product: string;
    category: string;
    region: string;
    quantity: number | null;
    sales: number;
    profit: number | null;
    discount_pct: number | null;
  }[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

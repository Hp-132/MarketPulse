import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import {
  AreaChart, Area, BarChart, Bar, ScatterChart, Scatter,
  PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine,
} from "recharts";
import {
  LayoutDashboard, ArrowLeftRight, BarChart2, MessageSquare,
  Package, Zap, Settings, Search, ChevronLeft, ChevronRight,
  Bell, CheckCircle2, AlertTriangle, Clock,
  TrendingDown, TrendingUp, ChevronDown, X,
} from "lucide-react";

/* ─── Brand palette ──────────────────────────────────────────────────────── */
const C = {
  aqua:        "#6EC6CA",
  teal:        "#08979D",
  deepTeal:    "#055B5C",
  lilac:       "#CCA8D8",
  purple:      "#8474A1",
  bg:          "#0F1420",
  sidebar:     "#090D17",
  card:        "#131927",
  panel:       "#1A2235",
  border:      "rgba(110,198,202,0.12)",
  text:        "#E8EDF5",
  muted:       "#7A8599",
  success:     "#34D399",
  warning:     "#FBBF24",
  danger:      "#F87171",
  // Chart-specific gradient anchor colors
  violet:      "#A78BFA",   // purple-to-violet series (Discount by Category)
  deepViolet:  "#6D28D9",   // dark end of violet gradient
  emerald:     "#34D399",   // green-to-emerald series (Discount by Brand)
  deepEmerald: "#065F46",   // dark end of emerald gradient
} as const;

const MONO = "'DM Mono', 'Courier New', monospace";

/* ─── Static UI labels ───────────────────────────────────────────────────── */
const CATEGORIES = ["Headphones","Kitchen Tools","Laptops","Moisturizer","Smart Tv","Smartphones"];

type SortKey = "pos" | "neu" | "crit" | "poor" | "avgRating";

/* ─── Filter types ───────────────────────────────────────────────────────── */
type Filters = {
  categories: string[];
  platforms:  string[];
  brands:     string[];
  search:     string;
};

const PLATFORMS = ["Amazon", "Flipkart"];

/* ─── Timestamp formatter ────────────────────────────────────────────────── */
const fmt = (iso: string) =>
  iso
    ? new Date(iso).toLocaleString("en-IN", {
        day: "2-digit", month: "short", year: "numeric",
        hour: "2-digit", minute: "2-digit", hour12: true,
      })
    : "—";

/* ─── MultiSelect dropdown ───────────────────────────────────────────────── */
function MultiSelect({
  label, options, selected, onChange,
}: {
  label: string;
  options: string[];
  selected: string[];
  onChange: (v: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const count = selected.length;
  const allSelected = count === options.length || count === 0;

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const toggle = useCallback((opt: string) => {
    onChange(selected.includes(opt) ? selected.filter(s => s !== opt) : [...selected, opt]);
  }, [selected, onChange]);

  const active = count > 0 && count < options.length;

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: "flex", alignItems: "center", gap: 5,
          padding: "4px 10px",
          border: `1px solid ${active ? C.aqua : C.border}`,
          borderRadius: 20,
          background: active ? `${C.aqua}14` : "transparent",
          color: active ? C.aqua : C.muted,
          fontSize: 12, fontWeight: 500, cursor: "pointer", whiteSpace: "nowrap",
          fontFamily: "'Inter',sans-serif", transition: "all 0.14s",
        }}
      >
        {label}
        {active && (
          <span style={{
            background: C.aqua, color: C.bg,
            borderRadius: 10, fontSize: 10, fontWeight: 700,
            padding: "1px 5px", lineHeight: 1.4,
          }}>{count}</span>
        )}
        <ChevronDown size={10} style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.14s" }} />
      </button>

      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 6px)", left: 0, zIndex: 999,
          background: C.card, border: `1px solid ${C.border}`,
          borderRadius: 10, padding: "6px 0", minWidth: 160,
          boxShadow: "0 16px 48px rgba(0,0,0,0.55)",
        }}>
          <button
            onClick={() => onChange(allSelected ? [] : options)}
            style={{
              width: "100%", textAlign: "left", padding: "6px 12px",
              background: "transparent", border: "none", cursor: "pointer",
              color: C.muted, fontSize: 11, fontWeight: 600,
              letterSpacing: "0.06em", textTransform: "uppercase",
              borderBottom: `1px solid ${C.border}`, marginBottom: 4,
            }}
          >{allSelected ? "Select all" : "Clear all"}</button>
          {options.map(opt => {
            const checked = selected.includes(opt);
            return (
              <button key={opt} onClick={() => toggle(opt)} style={{
                width: "100%", textAlign: "left", padding: "7px 12px",
                background: checked ? `${C.aqua}0E` : "transparent",
                border: "none", cursor: "pointer",
                color: checked ? C.aqua : C.text,
                fontSize: 12, fontWeight: checked ? 600 : 400,
                display: "flex", alignItems: "center", gap: 8,
                fontFamily: "'Inter',sans-serif",
              }}>
                <span style={{
                  width: 13, height: 13, borderRadius: 3, flexShrink: 0,
                  border: `1.5px solid ${checked ? C.aqua : C.muted}`,
                  background: checked ? C.aqua : "transparent",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  {checked && <span style={{ width: 7, height: 7, background: C.bg, borderRadius: 1, display: "block" }} />}
                </span>
                {opt}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ─── Active filter pills bar ────────────────────────────────────────────── */
function FilterPills({
  filters, onChange,
}: {
  filters: Filters;
  onChange: (f: Filters) => void;
}) {
  const pills: { label: string; onRemove: () => void }[] = [];
  filters.categories.forEach(c => pills.push({
    label: c,
    onRemove: () => onChange({ ...filters, categories: filters.categories.filter(x => x !== c) }),
  }));
  filters.platforms.forEach(p => pills.push({
    label: p,
    onRemove: () => onChange({ ...filters, platforms: filters.platforms.filter(x => x !== p) }),
  }));
  filters.brands.forEach(b => pills.push({
    label: b,
    onRemove: () => onChange({ ...filters, brands: filters.brands.filter(x => x !== b) }),
  }));

  if (pills.length === 0) return null;

  return (
    <div style={{
      padding: "6px 24px 0",
      display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap",
      background: C.bg,
    }}>
      <span style={{ fontSize: 11, color: C.muted, fontWeight: 500 }}>Filters:</span>
      {pills.map((p, i) => (
        <span key={i} style={{
          display: "inline-flex", alignItems: "center", gap: 5,
          padding: "2px 8px 2px 10px",
          background: `${C.teal}18`, border: `1px solid ${C.aqua}30`,
          borderRadius: 20, fontSize: 11, color: C.aqua, fontWeight: 500,
        }}>
          {p.label}
          <button onClick={p.onRemove} style={{
            background: "transparent", border: "none", cursor: "pointer",
            color: C.aqua, padding: 0, display: "flex", alignItems: "center", opacity: 0.7,
          }}><X size={10} /></button>
        </span>
      ))}
      <button
        onClick={() => onChange({ categories: [], platforms: [], brands: [], search: filters.search })}
        style={{
          background: "transparent", border: "none", cursor: "pointer",
          color: C.muted, fontSize: 11, padding: "2px 4px", textDecoration: "underline",
        }}
      >Clear all</button>
    </div>
  );
}

/* ─── Empty state ────────────────────────────────────────────────────────── */
function EmptyState() {
  return (
    <div style={{ padding: "80px 0", textAlign: "center" }}>
      <p style={{ fontSize: 28, margin: "0 0 12px" }}>🔍</p>
      <p style={{ fontSize: 14, color: C.muted, margin: "0 0 6px", fontWeight: 500 }}>
        No products match the current filters.
      </p>
      <p style={{ fontSize: 12, color: `${C.muted}88`, margin: 0 }}>
        Try removing a filter.
      </p>
    </div>
  );
}

/* ─── Insight annotation ─────────────────────────────────────────────────── */
function Insight({ text }: { text: string }) {
  return (
    <p style={{ fontSize: 12, color: "#7A8599", marginBottom: 8, marginTop: -8, lineHeight: 1.55 }}>
      {text}
    </p>
  );
}

/* ─── Shared primitives ──────────────────────────────────────────────────── */
function Card({ children, style = {} }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 12, ...style }}>
      {children}
    </div>
  );
}

type BadgeVariant = "teal"|"lilac"|"purple"|"success"|"warning"|"danger"|"amazon"|"flipkart"|"both";
const BADGE_STYLES: Record<BadgeVariant, { bg: string; color: string; border: string }> = {
  teal:     { bg: `${C.teal}18`,    color: C.aqua,    border: `${C.aqua}30`    },
  lilac:    { bg: `${C.lilac}18`,   color: C.lilac,   border: `${C.lilac}30`   },
  purple:   { bg: `${C.purple}18`,  color: C.lilac,   border: `${C.purple}30`  },
  success:  { bg: `${C.success}18`, color: C.success, border: `${C.success}30` },
  warning:  { bg: `${C.warning}18`, color: C.warning, border: `${C.warning}30` },
  danger:   { bg: `${C.danger}18`,  color: C.danger,  border: `${C.danger}30`  },
  amazon:   { bg: "#FF990018",      color: "#FF9900", border: "#FF990035"       },
  flipkart: { bg: "#2874F018",      color: "#6FA3F7", border: "#2874F030"       },
  both:     { bg: `${C.aqua}14`,    color: C.aqua,    border: `${C.aqua}30`    },
};
function Badge({ children, variant = "teal" }: { children: React.ReactNode; variant?: BadgeVariant }) {
  const s = BADGE_STYLES[variant];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", padding: "2px 8px", borderRadius: 20, fontSize: 11, fontWeight: 600, letterSpacing: "0.04em", background: s.bg, color: s.color, border: `1px solid ${s.border}` }}>
      {children}
    </span>
  );
}

function SecTitle({ title, sub }: { title: string; sub?: string }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <h2 style={{ fontSize: 14, fontWeight: 700, color: C.text, margin: 0, letterSpacing: "-0.01em" }}>{title}</h2>
      {sub && <p style={{ fontSize: 11, color: C.muted, margin: "3px 0 0" }}>{sub}</p>}
    </div>
  );
}

function CT({ active, payload, label, fmt: fmtFn }: { active?: boolean; payload?: any[]; label?: string; fmt?: (v: number, name?: string) => string }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#1C2740", border: `1px solid ${C.border}`, borderRadius: 8, padding: "8px 12px", fontSize: 12, boxShadow: "0 12px 40px rgba(0,0,0,0.6)" }}>
      {label && <p style={{ color: C.muted, marginBottom: 5, fontSize: 11, margin: "0 0 5px" }}>{label}</p>}
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, marginTop: i > 0 ? 3 : 0 }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: p.color || C.aqua, flexShrink: 0, display: "inline-block" }} />
          <span style={{ color: C.muted }}>{p.name}:</span>
          <span style={{ color: C.text, fontFamily: MONO, fontWeight: 500 }}>
            {fmtFn ? fmtFn(p.value, p.name) : p.value}
          </span>
        </div>
      ))}
    </div>
  );
}

function Sparkline({ data, id, color = C.aqua }: { data: { v: number }[]; id: string; color?: string }) {
  const gid = `sg-${id}`;
  return (
    <ResponsiveContainer width="100%" height={44}>
      <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor={color} stopOpacity={0.35} />
            <stop offset="100%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} fill={`url(#${gid})`} dot={false} isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

type KpiItem = { label: string; value: string; delta: string; up: boolean; spark: { v: number }[] };
function KPICard({ kpi, idx, sub }: { kpi: KpiItem; idx: number; sub?: string }) {
  const col = idx % 2 === 0 ? C.aqua : C.teal;
  return (
    <Card style={{ padding: "20px 20px 14px" }}>
      <p style={{ fontSize: 10, fontWeight: 600, color: C.muted, letterSpacing: "0.08em", textTransform: "uppercase", margin: "0 0 8px" }}>
        {kpi.label}
      </p>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: sub ? 4 : 12 }}>
        <span style={{ fontSize: 22, fontWeight: 800, fontFamily: MONO, color: C.text, letterSpacing: "-0.02em" }}>{kpi.value}</span>
        <span style={{ display: "flex", alignItems: "center", gap: 3, fontSize: 11, fontWeight: 600, color: kpi.up ? C.success : C.danger, background: kpi.up ? `${C.success}12` : `${C.danger}12`, padding: "3px 7px", borderRadius: 20, fontFamily: MONO, flexShrink: 0 }}>
          {kpi.up ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
          {kpi.delta}
        </span>
      </div>
      {sub && <p style={{ fontSize: 10, color: C.muted, margin: "0 0 8px", fontFamily: MONO }}>{sub}</p>}
      <Sparkline data={kpi.spark} id={`k${idx}`} color={col} />
    </Card>
  );
}

/* ─── PulseIcon ──────────────────────────────────────────────────────────── */
function PulseIcon() {
  return (
    <svg width="20" height="13" viewBox="0 0 24 14" fill="none" style={{ flexShrink: 0 }}>
      <polyline points="0,7 3,7 5,1 8,13 11,4 13,10 15.5,7 19,7 24,7"
        stroke={C.aqua} strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* ─── Navigation ─────────────────────────────────────────────────────────── */
const NAV = [
  { id: "overview",      label: "Overview",       icon: LayoutDashboard },
  { id: "crossplatform", label: "Cross-Platform",  icon: ArrowLeftRight  },
  { id: "statistics",    label: "Statistics",      icon: BarChart2       },
  { id: "sentiment",     label: "Sentiment",       icon: MessageSquare   },
  { id: "catalogue",     label: "Catalogue",       icon: Package         },
  { id: "pipeline",      label: "Pipeline Health", icon: Zap             },
  { id: "settings",      label: "Settings",        icon: Settings        },
];

/* ─── Sidebar ────────────────────────────────────────────────────────────── */
function Sidebar({ open, onToggle, active, onNav }: { open: boolean; onToggle: () => void; active: string; onNav: (id: string) => void }) {
  return (
    <div style={{ width: open ? 224 : 60, flexShrink: 0, background: C.sidebar, borderRight: `1px solid ${C.border}`, display: "flex", flexDirection: "column", transition: "width 0.22s cubic-bezier(0.4,0,0.2,1)", overflow: "hidden", height: "100vh", position: "sticky", top: 0 }}>
      <div style={{ padding: open ? "22px 18px 16px" : "22px 0 16px", display: "flex", alignItems: "center", gap: 10, justifyContent: open ? "flex-start" : "center", borderBottom: `1px solid ${C.border}` }}>
        <PulseIcon />
        {open && <span style={{ fontSize: 14, fontWeight: 800, color: C.text, letterSpacing: "-0.02em", whiteSpace: "nowrap" }}>MarketPulse</span>}
      </div>
      <nav style={{ flex: 1, padding: "16px 8px", display: "flex", flexDirection: "column", gap: 2 }}>
        {open && <p style={{ fontSize: 9, fontWeight: 600, color: C.muted, letterSpacing: "0.1em", textTransform: "uppercase", padding: "0 8px", margin: "0 0 6px" }}>Navigation</p>}
        {NAV.map(item => {
          const isActive = active === item.id;
          const Icon = item.icon;
          return (
            <button key={item.id} onClick={() => onNav(item.id)} style={{ display: "flex", alignItems: "center", gap: 9, padding: open ? "8px 10px" : "8px 0", justifyContent: open ? "flex-start" : "center", borderRadius: 8, border: "none", cursor: "pointer", width: "100%", background: isActive ? `${C.aqua}16` : "transparent", color: isActive ? C.aqua : C.muted, fontWeight: isActive ? 600 : 400, fontSize: 13, transition: "all 0.14s", outline: isActive ? `1px solid ${C.aqua}22` : "none", fontFamily: "'Inter',sans-serif" }}>
              <Icon size={15} style={{ flexShrink: 0 }} />
              {open && <span style={{ whiteSpace: "nowrap" }}>{item.label}</span>}
            </button>
          );
        })}
      </nav>
      <div style={{ padding: "12px 8px", borderTop: `1px solid ${C.border}`, display: "flex", justifyContent: open ? "flex-end" : "center" }}>
        <button onClick={onToggle} style={{ background: "transparent", border: `1px solid ${C.border}`, borderRadius: 6, padding: "5px 7px", cursor: "pointer", color: C.muted, display: "flex", alignItems: "center", justifyContent: "center" }}>
          {open ? <ChevronLeft size={13} /> : <ChevronRight size={13} />}
        </button>
      </div>
    </div>
  );
}

/* ─── TopBar ─────────────────────────────────────────────────────────────── */
function TopBar({
  filters, allCats, allBrands, onChange, lastSync,
}: {
  filters: Filters;
  allCats: string[];
  allBrands: string[];
  onChange: (f: Filters) => void;
  lastSync: string;
}) {
  return (
    <div style={{ height: 52, borderBottom: `1px solid ${C.border}`, padding: "0 24px", display: "flex", alignItems: "center", gap: 8, background: C.bg, flexShrink: 0 }}>
      <MultiSelect label="Category" options={allCats} selected={filters.categories} onChange={v => onChange({ ...filters, categories: v })} />
      <MultiSelect label="Platform" options={PLATFORMS} selected={filters.platforms} onChange={v => onChange({ ...filters, platforms: v })} />
      <MultiSelect label="Brand"    options={allBrands} selected={filters.brands}    onChange={v => onChange({ ...filters, brands: v })} />
      <div style={{ position: "relative", width: 230, marginLeft: 4 }}>
        <Search size={12} style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)", color: C.muted, pointerEvents: "none" }} />
        <input value={filters.search} onChange={e => onChange({ ...filters, search: e.target.value })} placeholder="Search products, brands…" style={{ width: "100%", padding: "5px 9px 5px 28px", background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontSize: 12, outline: "none", boxSizing: "border-box" }} />
      </div>
      <div style={{ flex: 1 }} />
      <span style={{ fontSize: 11, color: C.muted, fontFamily: MONO }}>
        Last sync: {lastSync || "—"}
      </span>
      <button style={{ background: "transparent", border: "none", cursor: "pointer", color: C.muted, display: "flex", alignItems: "center" }}>
        <Bell size={15} />
      </button>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Screen 1 — Overview
══════════════════════════════════════════════════════════════════════════════ */
function OverviewScreen({ data, filteredProducts }: { data: any; filteredProducts: any[] }) {
  const allKpis       = data.kpis        ?? [];
  const lastUpdated   = data.pipeline_health?.last_updated ?? null;
  const PRICE_BY_CAT  = data.priceByCat  ?? [];
  const DISC_BY_CAT   = data.discByCat   ?? [];
  const DISC_BY_BRAND = data.discByBrand ?? [];
  const TOP_DISCOUNTED = data.top20      ?? [];

  // ── Live KPIs recomputed from filteredProducts ───────────────────────────
  const liveKpis: KpiItem[] = useMemo(() => {
    const fp = filteredProducts;
    const n  = fp.length;

    // Products Tracked
    const totalVal = n;

    // Avg Price — take the lower of amazon/flipkart per product, or whichever exists
    const withPrice = fp.filter(p => p.amazon != null || p.flipkart != null);
    const avgPrice = withPrice.length
      ? Math.round(withPrice.reduce((s, p) => {
          const price = (p.amazon != null && p.flipkart != null)
            ? Math.min(p.amazon, p.flipkart)
            : (p.amazon ?? p.flipkart);
          return s + price;
        }, 0) / withPrice.length)
      : 0;

    // Avg Rating
    const withRating = fp.filter(p => p.rating != null);
    const avgRating = withRating.length
      ? Math.round(withRating.reduce((s, p) => s + p.rating, 0) / withRating.length * 100) / 100
      : 0;

    // Matched Pairs — products available on both platforms
    const matchedCount = fp.filter(p => p.avail === "both").length;

    // Brands — unique brands in filtered set
    const brandCount = new Set(fp.map(p => p.brand).filter(Boolean)).size;

    // ── Baseline values from static KPI JSON (full dataset) ─────────────
    // kpis[0] = Products Tracked, [1] = Avg Price, [2] = Avg Rating,
    // [3] = Matched Pairs, [4] = Brands
    const baseTotal   = parseInt((allKpis[0]?.value ?? "0").replace(/,/g, ""), 10) || n;
    const baseAvgPrice = parseInt((allKpis[1]?.value ?? "0").replace(/[₹,]/g, ""), 10) || avgPrice;
    const baseAvgRating = parseFloat((allKpis[2]?.value ?? "0").replace("★", "")) || avgRating;
    const baseMatched  = parseInt((allKpis[3]?.value ?? "0").replace(/,/g, ""), 10) || matchedCount;
    const baseBrands   = parseInt((allKpis[4]?.value ?? "0").replace(/,/g, ""), 10) || brandCount;

    const fmtDelta = (cur: number, base: number, isFloat = false) => {
      const diff = cur - base;
      if (diff === 0) return "—";
      const sign = diff > 0 ? "+" : "";
      return isFloat
        ? `${sign}${diff.toFixed(2)}`
        : `${sign}${Math.round(diff).toLocaleString()}`;
    };

    // Use the existing sparkline data from the static JSON (decorative)
    return [
      {
        label: "Products Tracked",
        value: totalVal.toLocaleString(),
        delta: fmtDelta(totalVal, baseTotal),
        up:    totalVal >= baseTotal,
        spark: allKpis[0]?.spark ?? [],
      },
      {
        label: "Avg. Price",
        value: `₹${avgPrice.toLocaleString()}`,
        delta: fmtDelta(avgPrice, baseAvgPrice),
        up:    avgPrice <= baseAvgPrice, // cheaper = good
        spark: allKpis[1]?.spark ?? [],
      },
      {
        label: "Avg. Rating",
        value: `${avgRating}★`,
        delta: fmtDelta(avgRating, baseAvgRating, true),
        up:    avgRating >= baseAvgRating,
        spark: allKpis[2]?.spark ?? [],
      },
      {
        label: "Matched Pairs",
        value: matchedCount.toLocaleString(),
        delta: fmtDelta(matchedCount, baseMatched),
        up:    matchedCount >= baseMatched,
        spark: allKpis[3]?.spark ?? [],
      },
      {
        label: "Brands",
        value: brandCount.toLocaleString(),
        delta: fmtDelta(brandCount, baseBrands),
        up:    brandCount >= baseBrands,
        spark: allKpis[4]?.spark ?? [],
      },
    ];
  }, [filteredProducts, allKpis]);

  // ── Products Tracked KPI subtitle ───────────────────────────────────────
  const trackedSub = lastUpdated ? `Last updated: ${fmt(lastUpdated)}` : undefined;

  // ── Insight: Price by Category ───────────────────────────────────────────
  const priceCatInsight = useMemo(() => {
    if (!PRICE_BY_CAT.length) return "";
    const activeCats = new Set(filteredProducts.map((p: any) => p.cat));
    const active = PRICE_BY_CAT.filter((r: any) => activeCats.size === 0 || activeCats.has(r.cat));
    const base = active.length ? active : PRICE_BY_CAT;
    const sorted = [...base].sort((a, b) => (b.premium ?? 0) - (a.premium ?? 0));
    const highCat = sorted[0]?.cat ?? "—";
    const highVal = (sorted[0]?.premium as number | undefined)?.toLocaleString() ?? "—";
    const lowCat  = sorted[sorted.length - 1]?.cat ?? "—";
    return `${highCat} has the highest avg premium price (₹${highVal}); ${lowCat} is most budget-friendly. Useful for category positioning.`;
  }, [PRICE_BY_CAT, filteredProducts]);

  // ── Insight: Discount by Category ────────────────────────────────────────
  const discCatInsight = useMemo(() => {
    if (!DISC_BY_CAT.length) return "";
    const activeCats = new Set(filteredProducts.map((p: any) => p.cat));
    const active = DISC_BY_CAT.filter((r: any) => activeCats.size === 0 || activeCats.has(r.cat));
    const base = active.length ? active : DISC_BY_CAT;
    const top = [...base].sort((a, b) => (b.avg ?? 0) - (a.avg ?? 0))[0];
    return `${top?.cat ?? "—"} offers the deepest avg discount (${top?.avg ?? 0}%). High discounts often signal competitive or oversupplied categories.`;
  }, [DISC_BY_CAT, filteredProducts]);

  return (
    <div style={{ maxWidth: 1320 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 14, marginBottom: 20 }}>
        {liveKpis.map((kpi: KpiItem, i: number) => (
          <KPICard key={i} kpi={kpi} idx={i} sub={i === 0 ? trackedSub : undefined} />
        ))}
      </div>

      {filteredProducts.length === 0 ? <EmptyState /> : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 14, marginBottom: 14 }}>
            <Card style={{ padding: 20 }}>
              <SecTitle title="Price by Category" sub="Budget / Mid-range / Premium tier avg. prices" />
              <Insight text={priceCatInsight} />
              <div style={{ display: "flex", gap: 14, marginBottom: 10 }}>
                {[{ l: "Budget", c: C.deepTeal }, { l: "Mid-range", c: C.teal }, { l: "Premium", c: C.aqua }].map(t => (
                  <div key={t.l} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: C.muted }}>
                    <span style={{ width: 9, height: 9, borderRadius: 2, background: t.c, display: "inline-block" }} />{t.l}
                  </div>
                ))}
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={PRICE_BY_CAT} barGap={3} barCategoryGap="30%">
                  <defs>
                    <linearGradient id="gBudget" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.deepTeal} /><stop offset="100%" stopColor={C.deepTeal} stopOpacity={0.5} /></linearGradient>
                    <linearGradient id="gMid"    x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.teal}     /><stop offset="100%" stopColor={C.teal}     stopOpacity={0.5} /></linearGradient>
                    <linearGradient id="gPrem"   x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.aqua}     /><stop offset="100%" stopColor={C.aqua}     stopOpacity={0.5} /></linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} stroke={`${C.muted}14`} />
                  <XAxis dataKey="cat" tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`} />
                  <Tooltip content={<CT fmt={(v: number) => `₹${v.toLocaleString()}`} />} />
                  <Bar dataKey="budget"  name="Budget"    fill="url(#gBudget)" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="mid"     name="Mid-range" fill="url(#gMid)"    radius={[3, 3, 0, 0]} />
                  <Bar dataKey="premium" name="Premium"   fill="url(#gPrem)"   radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>

            <Card style={{ padding: 20 }}>
              <SecTitle title="Discount by Category" sub="Average MRP discount %" />
              <Insight text={discCatInsight} />
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={DISC_BY_CAT} layout="vertical" barCategoryGap="25%">
                  <defs>
                    <linearGradient id="gDCat" x1="1" y1="0" x2="0" y2="0"><stop offset="0%" stopColor={C.violet} /><stop offset="100%" stopColor={C.deepViolet} stopOpacity={0.75} /></linearGradient>
                  </defs>
                  <CartesianGrid horizontal={false} stroke={`${C.muted}14`} />
                  <XAxis type="number" tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} domain={[0, 45]} />
                  <YAxis dataKey="cat" type="category" tick={{ fill: C.muted, fontSize: 9 }} axisLine={false} tickLine={false} width={82} />
                  <Tooltip content={<CT fmt={(v: number) => `${v}%`} />} />
                  <Bar dataKey="avg" name="Avg Discount" fill="url(#gDCat)" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>

          <Card style={{ padding: 20, marginBottom: 14 }}>
            <SecTitle title="Discount by Brand" sub="Top 10 brands ranked by average discount from MRP" />
            <ResponsiveContainer width="100%" height={170}>
              <BarChart data={DISC_BY_BRAND} barCategoryGap="38%">
                <defs>
                  <linearGradient id="gDBrand" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.emerald} /><stop offset="100%" stopColor={C.deepEmerald} stopOpacity={0.65} /></linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke={`${C.muted}14`} />
                <XAxis dataKey="brand" tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} />
                <Tooltip content={<CT fmt={(v: number) => `${v}%`} />} />
                <Bar dataKey="avg" name="Avg Discount" fill="url(#gDBrand)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card style={{ padding: 20 }}>
            <SecTitle title="Top 20 Most Discounted" sub="Ranked by discount from MRP across both platforms" />
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                    {["#", "Product", "Category", "Brand", "MRP", "Best Price", "Discount"].map(h => (
                      <th key={h} style={{ padding: "7px 10px", textAlign: h === "Discount" || h === "MRP" || h === "Best Price" ? "right" : "left", color: C.muted, fontWeight: 500, fontSize: 10, letterSpacing: "0.05em", textTransform: "uppercase", whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {TOP_DISCOUNTED.map((row: any, i: number) => (
                    <tr key={i} style={{ borderBottom: `1px solid ${C.border}18` }}>
                      <td style={{ padding: "8px 10px", color: C.muted, fontFamily: MONO, fontSize: 11, textAlign: "center" }}>{row.rank}</td>
                      <td style={{ padding: "8px 10px", color: C.text, fontWeight: 500, maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.name}</td>
                      <td style={{ padding: "8px 10px" }}><Badge variant="teal">{row.cat}</Badge></td>
                      <td style={{ padding: "8px 10px", color: C.muted }}>{row.brand}</td>
                      <td style={{ padding: "8px 10px", color: C.muted, fontFamily: MONO, textAlign: "right" }}>₹{row.mrp.toLocaleString()}</td>
                      <td style={{ padding: "8px 10px", color: C.text, fontFamily: MONO, fontWeight: 600, textAlign: "right" }}>₹{row.price.toLocaleString()}</td>
                      <td style={{ padding: "8px 10px", textAlign: "right" }}>
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 8 }}>
                          <div style={{ width: 52, height: 3, borderRadius: 2, background: C.border, overflow: "hidden" }}>
                            <div style={{ height: 3, borderRadius: 2, background: row.disc > 35 ? C.success : C.aqua, width: `${Math.min(row.disc, 100)}%` }} />
                          </div>
                          <span style={{ color: row.disc > 35 ? C.success : C.aqua, fontFamily: MONO, fontWeight: 700, fontSize: 12, minWidth: 38, textAlign: "right" }}>{row.disc.toFixed(1)}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Screen 2 — Cross-Platform
══════════════════════════════════════════════════════════════════════════════ */
function CrossPlatformScreen({ data, filteredProducts }: { data: any; filteredProducts: any[] }) {
  const MATCHED_PAIRS  = data.matchedPairs ?? [];
  const CHEAPER_BY_CAT = data.catCheaper  ?? [];
  const PRICE_CMP_CAT  = data.platComp    ?? [];

  // ── Insight: Platform Summary
  const platInsight = useMemo(() => {
    const amz = filteredProducts.filter(p => p.amazon != null);
    const fk  = filteredProducts.filter(p => p.flipkart != null);
    if (!amz.length && !fk.length) return "";
    const aAvg = amz.length ? Math.round(amz.reduce((s, p) => s + p.amazon, 0) / amz.length) : 0;
    const fAvg = fk.length  ? Math.round(fk.reduce( (s, p) => s + p.flipkart, 0) / fk.length) : 0;
    const cheaper = aAvg <= fAvg ? "Amazon" : "Flipkart";
    return `Amazon avg ₹${aAvg.toLocaleString()} (${amz.length} products) vs Flipkart avg ₹${fAvg.toLocaleString()} (${fk.length} products). ${cheaper} is cheaper on average.`;
  }, [filteredProducts]);

  // ── Insight: Matched Pairs
  const matchedInsight = useMemo(() => {
    const n = MATCHED_PAIRS.length;
    if (!n) return "";
    const aCheaper = MATCHED_PAIRS.filter((r: any) => r.cheaper === "Amazon").length;
    const fCheaper = MATCHED_PAIRS.filter((r: any) => r.cheaper === "Flipkart").length;
    return `${n} products matched across both platforms. Amazon is cheaper in ${aCheaper} cases, Flipkart in ${fCheaper} cases.`;
  }, [MATCHED_PAIRS]);

  return (
    <div style={{ maxWidth: 1320 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14, marginBottom: 20 }}>
        {[
          { label: "Matched Pairs",  value: String(MATCHED_PAIRS.length),  sub: "products on both platforms", color: C.text },
          { label: "Amazon Cheaper", value: `${CHEAPER_BY_CAT.reduce((s: number, r: any) => s + r.amazon, 0).toFixed(1)}%`, sub: "of matched pairs, all categories", color: C.aqua },
          { label: "Avg Price Gap",  value: `₹${MATCHED_PAIRS.length ? Math.round(MATCHED_PAIRS.reduce((s: any, r: any) => s + r.diff, 0) / MATCHED_PAIRS.length).toLocaleString() : "—"}`, sub: "absolute difference across matched pairs", color: C.lilac },
        ].map((s, i) => (
          <Card key={i} style={{ padding: 20 }}>
            <p style={{ fontSize: 10, color: C.muted, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", margin: "0 0 8px" }}>{s.label}</p>
            <p style={{ fontSize: 28, fontWeight: 800, fontFamily: MONO, color: s.color, margin: "0 0 4px", letterSpacing: "-0.02em" }}>{s.value}</p>
            <p style={{ fontSize: 12, color: C.muted, margin: 0 }}>{s.sub}</p>
          </Card>
        ))}
      </div>

      {filteredProducts.length === 0 ? <EmptyState /> : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 14 }}>
            <Card style={{ padding: 20 }}>
              <SecTitle title="Cheaper Platform by Category" sub="% of matched pairs where each platform is lower-priced" />
              <Insight text={platInsight} />
              <div style={{ display: "flex", gap: 14, marginBottom: 10 }}>
                {[{ l: "Amazon", c: "#FF9900" }, { l: "Flipkart", c: "#6FA3F7" }].map(t => (
                  <div key={t.l} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: C.muted }}>
                    <span style={{ width: 9, height: 9, borderRadius: 2, background: t.c, display: "inline-block" }} />{t.l}
                  </div>
                ))}
              </div>
              <ResponsiveContainer width="100%" height={210}>
                <BarChart data={CHEAPER_BY_CAT} layout="vertical" barCategoryGap="25%">
                  <CartesianGrid horizontal={false} stroke={`${C.muted}14`} />
                  <XAxis type="number" tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} domain={[0, 100]} />
                  <YAxis dataKey="cat" type="category" tick={{ fill: C.muted, fontSize: 9 }} axisLine={false} tickLine={false} width={88} />
                  <Tooltip content={<CT fmt={(v: number) => `${v}%`} />} />
                  <Bar dataKey="amazon"   name="Amazon"   fill="#FF9900" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="flipkart" name="Flipkart" fill="#6FA3F7" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>

            <Card style={{ padding: 20 }}>
              <SecTitle title="Avg. Price Comparison" sub="Amazon vs Flipkart average price by category" />
              <div style={{ display: "flex", gap: 14, marginBottom: 10 }}>
                {[{ l: "Amazon", c: "#FF9900" }, { l: "Flipkart", c: "#6FA3F7" }].map(t => (
                  <div key={t.l} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: C.muted }}>
                    <span style={{ width: 9, height: 9, borderRadius: 2, background: t.c, display: "inline-block" }} />{t.l}
                  </div>
                ))}
              </div>
              <ResponsiveContainer width="100%" height={210}>
                <BarChart data={PRICE_CMP_CAT} barGap={4} barCategoryGap="30%">
                  <CartesianGrid vertical={false} stroke={`${C.muted}14`} />
                  <XAxis dataKey="cat" tick={{ fill: C.muted, fontSize: 9 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`} />
                  <Tooltip content={<CT fmt={(v: number) => `₹${v.toLocaleString()}`} />} />
                  <Bar dataKey="amazon"   name="Amazon"   fill="#FF9900" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="flipkart" name="Flipkart" fill="#6FA3F7" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>

          <Card style={{ padding: 20 }}>
            <SecTitle title="Matched Pair Table" sub="Products tracked on both platforms with live price delta" />
            <Insight text={matchedInsight} />
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                  {["ID", "Product", "Category", "Brand", "Amazon", "Flipkart", "Δ Price", "Cheaper"].map(h => (
                    <th key={h} style={{ padding: "7px 10px", textAlign: "left", color: C.muted, fontWeight: 500, fontSize: 10, letterSpacing: "0.05em", textTransform: "uppercase", whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {MATCHED_PAIRS.map((row: any, i: number) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}18` }}>
                    <td style={{ padding: "8px 10px", color: C.muted, fontFamily: MONO, fontSize: 11 }}>{row.id}</td>
                    <td style={{ padding: "8px 10px", color: C.text, fontWeight: 500, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.name}</td>
                    <td style={{ padding: "8px 10px" }}><Badge variant="teal">{row.cat}</Badge></td>
                    <td style={{ padding: "8px 10px", color: C.muted }}>{row.brand}</td>
                    <td style={{ padding: "8px 10px", fontFamily: MONO, color: row.cheaper === "Amazon" ? C.success : C.text }}>₹{row.amazon.toLocaleString()}</td>
                    <td style={{ padding: "8px 10px", fontFamily: MONO, color: row.cheaper === "Flipkart" ? C.success : C.text }}>₹{row.flipkart.toLocaleString()}</td>
                    <td style={{ padding: "8px 10px", color: C.muted, fontFamily: MONO }}>₹{row.diff.toLocaleString()}</td>
                    <td style={{ padding: "8px 10px" }}><Badge variant={row.cheaper === "Amazon" ? "amazon" : "flipkart"}>{row.cheaper}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Screen 3 — Statistics
══════════════════════════════════════════════════════════════════════════════ */
function StatisticsScreen({ data, filteredProducts }: { data: any; filteredProducts: any[] }) {
  const SCATTER_DATA = data.scatterData ?? [];
  const VOLATILITY   = data.cvData      ?? [];
  const OUTLIERS     = data.outliers    ?? [];
  const pearsonR     = data.pearsonR    ?? 0.155;

  // ── Insight: Scatter / Pearson
  const scatterInsight = useMemo(() => {
    const r = pearsonR;
    const interp = r > 0.3
      ? "Moderate positive link — pricier products tend to be rated higher."
      : r < -0.3
        ? "Higher price does not guarantee better rating."
        : "Weak correlation — price and rating are largely independent.";
    return `Pearson r = ${r >= 0 ? "+" : ""}${r.toFixed(3)}. ${interp}`;
  }, [pearsonR]);

  // ── Insight: Volatility
  const volatilityInsight = "High coefficient of variation (CV) means prices vary widely within that category, signalling a fragmented or competitive market.";

  // ── Insight: Outliers
  const outlierInsight = useMemo(() => {
    const n = OUTLIERS.length;
    return `${n} product${n !== 1 ? "s" : ""} flagged with z-score > 2. These are priced unusually high or low vs their category average — review for data quality or genuine anomalies.`;
  }, [OUTLIERS]);

  return (
    <div style={{ maxWidth: 1320 }}>
      {filteredProducts.length === 0 ? <EmptyState /> : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 14, marginBottom: 14 }}>
            <Card style={{ padding: 20 }}>
              <SecTitle title="Price–Rating Scatter" sub={`All ${SCATTER_DATA.length.toLocaleString()} products — price vs. average customer rating`} />
              <Insight text={scatterInsight} />
              <ResponsiveContainer width="100%" height={290}>
                <ScatterChart margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={`${C.muted}14`} />
                  <XAxis type="number" dataKey="price"  name="Price"  tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`} />
                  <YAxis type="number" dataKey="rating" name="Rating" tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} domain={[2, 5]} tickFormatter={v => `${v}★`} />
                  <Tooltip content={(props: any) => {
                    if (!props.active || !props.payload?.length) return null;
                    const d = props.payload[0]?.payload;
                    return (
                      <div style={{ background: "#1C2740", border: `1px solid ${C.border}`, borderRadius: 8, padding: "8px 12px", fontSize: 12 }}>
                        <p style={{ color: C.muted, margin: "0 0 3px" }}>Price: <span style={{ color: C.text, fontFamily: MONO }}>₹{d?.price?.toLocaleString()}</span></p>
                        <p style={{ color: C.muted, margin: 0 }}>Rating: <span style={{ color: C.text, fontFamily: MONO }}>{d?.rating}★</span></p>
                      </div>
                    );
                  }} />
                  <Scatter data={SCATTER_DATA} fill={C.aqua} fillOpacity={0.65} r={5} />
                </ScatterChart>
              </ResponsiveContainer>
            </Card>

            <Card style={{ padding: 20, display: "flex", flexDirection: "column", gap: 18, justifyContent: "center" }}>
              <div>
                <p style={{ fontSize: 10, color: C.muted, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", margin: "0 0 8px" }}>Pearson r Coefficient</p>
                <p style={{ fontSize: 52, fontWeight: 800, fontFamily: MONO, color: C.aqua, letterSpacing: "-0.03em", margin: 0, lineHeight: 1 }}>{pearsonR >= 0 ? "+" : ""}{pearsonR.toFixed(3)}</p>
                <p style={{ fontSize: 12, color: C.muted, marginTop: 8, lineHeight: 1.6 }}>
                  Weak positive correlation — higher-priced products trend toward better ratings, though category and brand are stronger predictors.
                </p>
              </div>
              <div style={{ padding: "12px 14px", background: `${C.deepTeal}1E`, border: `1px solid ${C.deepTeal}55`, borderRadius: 8 }}>
                <p style={{ fontSize: 11, color: C.aqua, fontWeight: 600, margin: "0 0 5px" }}>R² = {(pearsonR * pearsonR).toFixed(3)}</p>
                <p style={{ fontSize: 11, color: C.muted, lineHeight: 1.6, margin: 0 }}>Price explains ~{(pearsonR * pearsonR * 100).toFixed(1)}% of rating variance. Significant unexplained variance remains across all categories.</p>
              </div>
              <div>
                <p style={{ fontSize: 11, color: C.muted, margin: "0 0 3px" }}>Sample size</p>
                <p style={{ fontSize: 20, fontWeight: 700, fontFamily: MONO, color: C.text, margin: 0 }}>{SCATTER_DATA.length.toLocaleString()} <span style={{ fontSize: 12, fontWeight: 400, color: C.muted }}>products</span></p>
              </div>
            </Card>
          </div>

          <Card style={{ padding: 20, marginBottom: 14 }}>
            <SecTitle title="Price Volatility by Category" sub="Coefficient of Variation (σ/μ) — higher value = more dispersed pricing within category" />
            <Insight text={volatilityInsight} />
            <ResponsiveContainer width="100%" height={170}>
              <BarChart data={VOLATILITY} barCategoryGap="40%">
                <defs>
                  <linearGradient id="gVol" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.lilac} stopOpacity={0.9} /><stop offset="100%" stopColor={C.purple} stopOpacity={0.55} /></linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke={`${C.muted}14`} />
                <XAxis dataKey="cat" tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} domain={[0, 1]} tickFormatter={v => v.toFixed(1)} />
                <ReferenceLine y={0.6} stroke={C.warning} strokeDasharray="4 4" strokeOpacity={0.55} />
                <Tooltip content={<CT fmt={(v: number) => v.toFixed(2)} />} />
                <Bar dataKey="cv" name="Coeff. of Variation" fill="url(#gVol)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <p style={{ fontSize: 11, color: C.muted, marginTop: 6 }}>
              Dashed line at 0.60 — <span style={{ color: C.warning }}>high volatility threshold</span>. Clothing shows the most pricing dispersion.
            </p>
          </Card>

          <Card style={{ padding: 20 }}>
            <SecTitle title="Price Outliers" sub="Products with z-score > 3 relative to their category mean" />
            <Insight text={outlierInsight} />
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                  {["Product", "Category", "Brand", "Price", "Category Avg", "Z-Score"].map(h => (
                    <th key={h} style={{ padding: "7px 10px", textAlign: "left", color: C.muted, fontWeight: 500, fontSize: 10, letterSpacing: "0.05em", textTransform: "uppercase" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {OUTLIERS.map((row: any, i: number) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}18` }}>
                    <td style={{ padding: "9px 10px", color: C.text, fontWeight: 500 }}>{row.name}</td>
                    <td style={{ padding: "9px 10px" }}><Badge variant="teal">{row.cat}</Badge></td>
                    <td style={{ padding: "9px 10px", color: C.muted }}>{row.brand}</td>
                    <td style={{ padding: "9px 10px", fontFamily: MONO, fontWeight: 600, color: C.text }}>₹{row.price.toLocaleString()}</td>
                    <td style={{ padding: "9px 10px", fontFamily: MONO, color: C.muted }}>₹{row.avgCat.toLocaleString()}</td>
                    <td style={{ padding: "9px 10px" }}>
                      <span style={{ display: "inline-flex", alignItems: "center", padding: "3px 9px", borderRadius: 6, fontSize: 12, fontWeight: 700, fontFamily: MONO, color: row.z > 4 ? C.danger : C.warning, background: row.z > 4 ? `${C.danger}14` : `${C.warning}14`, border: `1px solid ${row.z > 4 ? C.danger : C.warning}28` }}>
                        z = {row.z.toFixed(2)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Screen 4 — Sentiment
══════════════════════════════════════════════════════════════════════════════ */
function SentimentScreen({ data, filteredProducts }: { data: any; filteredProducts: any[] }) {
  const SENTIMENT_DONUT = data.sentDonut ?? [];
  const SENTIMENT_TABLE = data.sentTable ?? [];
  const [sortKey, setSortKey] = useState<SortKey>("avgRating");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const sorted = useMemo(() => {
    return [...SENTIMENT_TABLE].sort((a, b) => {
      const diff = (b[sortKey] as number) - (a[sortKey] as number);
      return sortDir === "desc" ? diff : -diff;
    });
  }, [sortKey, sortDir, SENTIMENT_TABLE]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === "desc" ? "asc" : "desc");
    else { setSortKey(key); setSortDir("desc"); }
  };

  // ── Insight: Sentiment distribution — posPct computed from filteredProducts
  const sentInsight = useMemo(() => {
    const withRating = filteredProducts.filter((p: any) => p.rating != null);
    const posPct = withRating.length
      ? Math.round(withRating.filter((p: any) => p.rating >= 4.0).length / withRating.length * 100)
      : 0;
    return `Sentiment is rating-derived (≥4.5 Positive, 3.5–4.4 Neutral, <3.5 Negative) — not NLP. ${posPct}% of products score Positive.`;
  }, [filteredProducts]);

  // ── Insight: Ratings by Category
  const ratingCatInsight = "Categories where <70% of products are rated above 4.0 may have quality or satisfaction issues worth investigating.";

  const cols: { key: SortKey; label: string; color: string }[] = [
    { key: "pos",       label: "Positive",  color: C.success },
    { key: "neu",       label: "Neutral",   color: C.muted   },
    { key: "crit",      label: "Critical",  color: C.warning },
    { key: "poor",      label: "Poor",      color: C.danger  },
    { key: "avgRating", label: "Avg ★",     color: C.aqua    },
  ];

  // Live positive % from filteredProducts
  const livePosPct = useMemo(() => {
    const withRating = filteredProducts.filter(p => p.rating != null);
    if (!withRating.length) return 0;
    const pos = withRating.filter(p => p.rating >= 4.0).length;
    return Math.round((pos / withRating.length) * 100);
  }, [filteredProducts]);

  return (
    <div style={{ maxWidth: 1320 }}>
      <div style={{ padding: "10px 14px", background: `${C.purple}14`, border: `1px solid ${C.purple}30`, borderRadius: 8, marginBottom: 18, display: "flex", alignItems: "flex-start", gap: 10 }}>
        <span style={{ fontSize: 14, flexShrink: 0, marginTop: 1 }}>ℹ</span>
        <p style={{ fontSize: 12, color: C.muted, margin: 0, lineHeight: 1.6 }}>
          <span style={{ color: C.lilac, fontWeight: 600 }}>Proxy metric — not NLP.</span>{" "}
          Sentiment tiers are derived from star ratings only, not review-text analysis. Positive ≥4★ · Neutral 3–3.9★ · Critical 2–2.9★ · Poor &lt;2★. Treat as a structural signal, not ground-truth sentiment.
        </p>
      </div>

      {filteredProducts.length === 0 ? <EmptyState /> : (
        <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 14 }}>
          <Card style={{ padding: 20 }}>
            <SecTitle title="Sentiment Mix" sub={`Rating-derived distribution across ${filteredProducts.length.toLocaleString()} filtered products`} />
            <Insight text={sentInsight} />
            <div style={{ position: "relative", height: 230 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={SENTIMENT_DONUT} cx="50%" cy="50%" innerRadius={68} outerRadius={104} dataKey="value" paddingAngle={3} startAngle={90} endAngle={-270}>
                    {SENTIMENT_DONUT.map((entry: any, i: number) => <Cell key={i} fill={entry.color} stroke="none" />)}
                  </Pie>
                  <Tooltip formatter={(v: any) => [`${v}%`, ""]} contentStyle={{ background: "#1C2740", border: `1px solid ${C.border}`, borderRadius: 8, fontSize: 12 }} itemStyle={{ color: C.text }} labelStyle={{ display: "none" }} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", textAlign: "center", pointerEvents: "none" }}>
                <p style={{ fontSize: 26, fontWeight: 800, fontFamily: MONO, color: C.aqua, margin: 0, lineHeight: 1 }}>{livePosPct}%</p>
                <p style={{ fontSize: 11, color: C.muted, margin: "3px 0 0" }}>Positive</p>
              </div>
            </div>
            <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 8 }}>
              {SENTIMENT_DONUT.map((s: any, i: number) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 9, height: 9, borderRadius: 2, background: s.color, display: "inline-block", flexShrink: 0 }} />
                    <span style={{ fontSize: 12, color: C.muted }}>{s.label}</span>
                  </div>
                  <span style={{ fontSize: 12, fontFamily: MONO, color: C.text, fontWeight: 600 }}>{s.value}%</span>
                </div>
              ))}
            </div>
          </Card>

          <Card style={{ padding: 20 }}>
            <SecTitle title="Category Sentiment Breakdown" sub="Click column headers to sort — all values are % of products in category" />
            <Insight text={ratingCatInsight} />
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                  <th style={{ padding: "7px 10px", textAlign: "left", color: C.muted, fontWeight: 500, fontSize: 10, letterSpacing: "0.05em", textTransform: "uppercase" }}>Category</th>
                  {cols.map(({ key, label }) => (
                    <th key={key} onClick={() => toggleSort(key)} style={{ padding: "7px 10px", textAlign: "right", color: sortKey === key ? C.aqua : C.muted, fontWeight: 500, fontSize: 10, letterSpacing: "0.05em", textTransform: "uppercase", cursor: "pointer", userSelect: "none", whiteSpace: "nowrap" }}>
                      {label} {sortKey === key ? (sortDir === "desc" ? "↓" : "↑") : ""}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((row: any, i: number) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}18` }}>
                    <td style={{ padding: "9px 10px", color: C.text, fontWeight: 500 }}>{row.cat}</td>
                    <td style={{ padding: "9px 10px", textAlign: "right", color: C.success, fontFamily: MONO }}>{row.pos}%</td>
                    <td style={{ padding: "9px 10px", textAlign: "right", color: C.muted,   fontFamily: MONO }}>{row.neu}%</td>
                    <td style={{ padding: "9px 10px", textAlign: "right", color: C.warning, fontFamily: MONO }}>{row.crit}%</td>
                    <td style={{ padding: "9px 10px", textAlign: "right", color: C.danger,  fontFamily: MONO }}>{row.poor}%</td>
                    <td style={{ padding: "9px 10px", textAlign: "right", color: C.aqua,    fontFamily: MONO, fontWeight: 700 }}>{row.avgRating.toFixed(2)}★</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      )}
    </div>
  );
}

/* ─── Rating by brand helper ─────────────────────────────────────────────── */
function build_rating_by_brand_local(products: any[]) {
  const map: Record<string, { sum: number; count: number }> = {};
  for (const p of products) {
    if (!p.brand || p.rating == null) continue;
    if (!map[p.brand]) map[p.brand] = { sum: 0, count: 0 };
    map[p.brand].sum   += p.rating;
    map[p.brand].count += 1;
  }
  return Object.entries(map)
    .filter(([, v]) => v.count >= 2)
    .map(([brand, v]) => ({ brand, rating: Math.round((v.sum / v.count) * 100) / 100 }))
    .sort((a, b) => b.rating - a.rating)
    .slice(0, 10);
}

/* ═══════════════════════════════════════════════════════════════════════════
   Screen 5 — Catalogue
══════════════════════════════════════════════════════════════════════════════ */
function CatalogueScreen({ data, filteredProducts }: { data: any; filteredProducts: any[] }) {
  const CATALOGUE       = filteredProducts;
  const BRAND_PANEL     = data.brandPanel ?? [];
  const RATING_BY_CAT   = data.sentTable?.map((s: any) => ({ cat: s.cat, rating: s.avgRating })) ?? [];
  const RATING_BY_BRAND = build_rating_by_brand_local(filteredProducts);

  const [search, setSearch] = useState("");
  const [priceMax, setPriceMax] = useState(200000);

  // ── Insight: Ratings by Category
  const ratingCatInsight = "Categories where <70% of products are rated above 4.0 may have quality or satisfaction issues worth investigating.";

  const filtered = useMemo(() => {
    return CATALOGUE.filter((p: any) => {
      const price = p.amazon ?? p.flipkart ?? 0;
      return (
        price <= priceMax &&
        (search === "" || (p.name ?? "").toLowerCase().includes(search.toLowerCase()) || (p.brand ?? "").toLowerCase().includes(search.toLowerCase()))
      );
    });
  }, [CATALOGUE, search, priceMax]);

  return (
    <div style={{ maxWidth: 1320 }}>
      <Card style={{ padding: "12px 18px", marginBottom: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <div style={{ position: "relative", flex: "0 0 200px" }}>
            <Search size={12} style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)", color: C.muted, pointerEvents: "none" }} />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search product or brand…" style={{ width: "100%", padding: "6px 8px 6px 27px", background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, color: C.text, fontSize: 12, outline: "none", boxSizing: "border-box" }} />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 7, marginLeft: "auto" }}>
            <span style={{ fontSize: 11, color: C.muted, whiteSpace: "nowrap" }}>Max Price:</span>
            <input type="range" min={0} max={200000} step={5000} value={priceMax} onChange={e => setPriceMax(Number(e.target.value))} style={{ accentColor: C.aqua, width: 110, cursor: "pointer" }} />
            <span style={{ fontSize: 11, fontFamily: MONO, color: C.text, whiteSpace: "nowrap", minWidth: 44 }}>₹{(priceMax / 1000).toFixed(0)}k</span>
          </div>
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "188px 1fr", gap: 14, marginBottom: 14 }}>
        <Card style={{ padding: 14 }}>
          <p style={{ fontSize: 10, fontWeight: 600, color: C.muted, letterSpacing: "0.08em", textTransform: "uppercase", margin: "0 0 10px" }}>Brands ({BRAND_PANEL.length})</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            {BRAND_PANEL.map((b: any, i: number) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 5, borderBottom: i < BRAND_PANEL.length - 1 ? `1px solid ${C.border}14` : "none" }}>
                <div>
                  <p style={{ fontSize: 12, color: C.text, margin: 0, fontWeight: 500 }}>{b.brand}</p>
                  <p style={{ fontSize: 10, color: C.muted, margin: 0, fontFamily: MONO }}>{b.count}</p>
                </div>
                <span style={{ fontSize: 9, fontWeight: 600, padding: "2px 5px", borderRadius: 4, color: b.avail === "amazon" ? "#FF9900" : b.avail === "flipkart" ? "#6FA3F7" : C.aqua, background: b.avail === "amazon" ? "#FF990012" : b.avail === "flipkart" ? "#2874F012" : `${C.aqua}12` }}>
                  {b.avail === "both" ? "both" : b.avail}
                </span>
              </div>
            ))}
          </div>
        </Card>

        <Card style={{ padding: 18 }}>
          <SecTitle title="Product Catalogue" sub={`${filtered.length} of ${CATALOGUE.length} products match current filters`} />
          {filtered.length === 0 ? (
            <div style={{ padding: "40px 0", textAlign: "center" }}>
              <p style={{ fontSize: 14, color: C.muted, margin: "0 0 6px" }}>No products match the active filters.</p>
              <p style={{ fontSize: 12, color: `${C.muted}88`, margin: 0 }}>Try changing Category, Platform, or Brand filters above.</p>
            </div>
          ) : (
            <div style={{ overflowY: "auto", maxHeight: 400 }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead style={{ position: "sticky", top: 0, background: C.card, zIndex: 1 }}>
                  <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                    {["Product", "Brand", "Category", "Amazon", "Flipkart", "Rating", "Disc", "Avail"].map(h => (
                      <th key={h} style={{ padding: "7px 9px", textAlign: "left", color: C.muted, fontWeight: 500, fontSize: 10, letterSpacing: "0.05em", textTransform: "uppercase", whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((row: any, i: number) => (
                    <tr key={i} style={{ borderBottom: `1px solid ${C.border}18` }}>
                      <td style={{ padding: "8px 9px", color: C.text, fontWeight: 500, maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.name}</td>
                      <td style={{ padding: "8px 9px", color: C.muted, whiteSpace: "nowrap" }}>{row.brand}</td>
                      <td style={{ padding: "8px 9px" }}><Badge variant="teal">{row.cat}</Badge></td>
                      <td style={{ padding: "8px 9px", fontFamily: MONO, color: row.amazon ? C.text : C.muted, whiteSpace: "nowrap" }}>{row.amazon ? `₹${row.amazon.toLocaleString()}` : "—"}</td>
                      <td style={{ padding: "8px 9px", fontFamily: MONO, color: row.flipkart ? C.text : C.muted, whiteSpace: "nowrap" }}>{row.flipkart ? `₹${row.flipkart.toLocaleString()}` : "—"}</td>
                      <td style={{ padding: "8px 9px", color: C.text, fontFamily: MONO }}>{row.rating}★</td>
                      <td style={{ padding: "8px 9px", color: row.disc > 30 ? C.success : C.muted, fontFamily: MONO }}>{row.disc > 0 ? `${row.disc}%` : "—"}</td>
                      <td style={{ padding: "8px 9px" }}>
                        <Badge variant={row.avail === "amazon" ? "amazon" : row.avail === "flipkart" ? "flipkart" : "both"}>
                          {row.avail === "both" ? "Both" : row.avail === "amazon" ? "Amazon" : "Flipkart"}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <Card style={{ padding: 20 }}>
          <SecTitle title="Rating by Category" sub="Average star rating per category" />
          <Insight text={ratingCatInsight} />
          <ResponsiveContainer width="100%" height={170}>
            <BarChart data={RATING_BY_CAT} barCategoryGap="40%">
              <defs>
                <linearGradient id="gRatCat" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.aqua} /><stop offset="100%" stopColor={C.deepTeal} stopOpacity={0.5} /></linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke={`${C.muted}14`} />
              <XAxis dataKey="cat" tick={{ fill: C.muted, fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} domain={[3.5, 5]} tickFormatter={v => `${v}★`} />
              <ReferenceLine y={4.0} stroke={C.teal} strokeDasharray="4 4" strokeOpacity={0.5} />
              <Tooltip content={<CT fmt={(v: number) => `${v.toFixed(2)}★`} />} />
              <Bar dataKey="rating" name="Avg Rating" fill="url(#gRatCat)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card style={{ padding: 20 }}>
          <SecTitle title="Rating by Brand" sub="Average star rating per brand (min 2 products)" />
          <ResponsiveContainer width="100%" height={170}>
            <BarChart data={RATING_BY_BRAND} barCategoryGap="40%">
              <defs>
                <linearGradient id="gRatBrand" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.teal} /><stop offset="100%" stopColor={C.deepTeal} stopOpacity={0.5} /></linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke={`${C.muted}14`} />
              <XAxis dataKey="brand" tick={{ fill: C.muted, fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: C.muted, fontSize: 10 }} axisLine={false} tickLine={false} domain={[3.6, 4.4]} tickFormatter={v => `${v}★`} />
              <Tooltip content={<CT fmt={(v: number) => `${v.toFixed(2)}★`} />} />
              <Bar dataKey="rating" name="Avg Rating" fill="url(#gRatBrand)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Screen 6 — Pipeline Health
══════════════════════════════════════════════════════════════════════════════ */
function PipelineScreen({ data }: { data: any }) {
  const PLATFORM_SUMMARY = data.platformSummary ?? [];
  const ETL_LOGS         = data.pipelineLogs    ?? [];
  return (
    <div style={{ maxWidth: 1320 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 20 }}>
        {PLATFORM_SUMMARY.map((p: any, i: number) => (
          <Card key={i} style={{ padding: 22 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 18 }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: C.success, display: "inline-block" }} />
                  <h3 style={{ fontSize: 16, fontWeight: 700, color: C.text, margin: 0 }}>{p.platform}</h3>
                </div>
                <p style={{ fontSize: 11, color: C.muted, margin: 0, fontFamily: MONO }}>Last run: {p.lastRun}</p>
              </div>
              <Badge variant="success">{p.status}</Badge>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14, marginBottom: 18 }}>
              {[{ l: "Products", v: p.products.toLocaleString() }, { l: "Brands", v: String(p.brands) }, { l: "Categories", v: String(p.cats) }].map(stat => (
                <div key={stat.l}>
                  <p style={{ fontSize: 10, color: C.muted, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 4px" }}>{stat.l}</p>
                  <p style={{ fontSize: 22, fontWeight: 700, fontFamily: MONO, color: C.text, margin: 0 }}>{stat.v}</p>
                </div>
              ))}
            </div>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                <span style={{ fontSize: 11, color: C.muted }}>Pipeline health score</span>
                <span style={{ fontSize: 11, fontFamily: MONO, color: C.success, fontWeight: 600 }}>{p.health}%</span>
              </div>
              <div style={{ height: 5, borderRadius: 4, background: C.border }}>
                <div style={{ height: 5, borderRadius: 4, background: `linear-gradient(90deg, ${C.deepTeal}, ${C.aqua})`, width: `${p.health}%`, transition: "width 0.6s ease" }} />
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Card style={{ padding: 22 }}>
        <SecTitle title="ETL Activity Log" sub="Recent pipeline runs" />
        <div style={{ display: "flex", flexDirection: "column" }}>
          {ETL_LOGS.map((log: any, i: number) => {
            const isLast = i === ETL_LOGS.length - 1;
            const statusColor = log.status === "success" ? C.success : log.status === "error" ? C.danger : C.warning;
            return (
              <div key={log.id} style={{ display: "flex", gap: 16, paddingBottom: isLast ? 0 : 14, position: "relative" }}>
                {!isLast && <div style={{ position: "absolute", left: 14, top: 28, bottom: 0, width: 1, background: `${C.border}` }} />}
                <div style={{ flexShrink: 0, width: 28, height: 28, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", background: `${statusColor}14`, border: `1.5px solid ${statusColor}35`, zIndex: 1 }}>
                  {log.status === "success" ? <CheckCircle2 size={13} color={statusColor} /> : log.status === "error" ? <AlertTriangle size={13} color={statusColor} /> : <Clock size={13} color={statusColor} />}
                </div>
                <div style={{ flex: 1, paddingTop: 4 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: log.note ? 3 : 0 }}>
                    <span style={{ fontSize: 11, fontFamily: MONO, color: C.muted, flexShrink: 0 }}>{log.ts}</span>
                    <Badge variant={log.platform === "Amazon" ? "amazon" : "flipkart"}>{log.platform}</Badge>
                    <span style={{ fontSize: 12, color: C.text, fontWeight: 500 }}>{log.cat}</span>
                    <span style={{ marginLeft: "auto", fontSize: 11, fontFamily: MONO, color: C.muted, flexShrink: 0 }}>{log.dur}</span>
                    {log.count > 0 && <span style={{ fontSize: 11, fontFamily: MONO, color: C.aqua, flexShrink: 0 }}>{log.count.toLocaleString()} products</span>}
                  </div>
                  {log.note && <p style={{ fontSize: 11, color: statusColor, margin: 0, opacity: 0.85 }}>{log.note}</p>}
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Screen 7 — Settings
══════════════════════════════════════════════════════════════════════════════ */
function SettingsScreen({ data }: { data: any }) {
  const [activeCats, setActiveCats] = useState<string[]>([...CATEGORIES]);
  const toggleCat = (cat: string) =>
    setActiveCats(prev => prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]);

  const ph = data.pipeline_health ?? {};
  const sources: any[] = ph.sources ?? [];
  const etlRuns: any[] = ph.etl_runs ?? [];
  const lastUpdated: string = ph.last_updated ?? "";

  return (
    <div style={{ maxWidth: 720 }}>
      <h1 style={{ fontSize: 20, fontWeight: 800, color: C.text, margin: "0 0 24px", letterSpacing: "-0.02em" }}>Settings</h1>

      <Card style={{ padding: 24, marginBottom: 14 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: C.text, margin: "0 0 4px" }}>Active Categories</h3>
        <p style={{ fontSize: 12, color: C.muted, margin: "0 0 16px" }}>Control which categories are included in scraping jobs and analysis views.</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {CATEGORIES.map(cat => {
            const active = activeCats.includes(cat);
            return (
              <button key={cat} onClick={() => toggleCat(cat)} style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 14px", borderRadius: 24, fontSize: 13, fontWeight: 500, cursor: "pointer", border: `1.5px solid ${active ? C.aqua : C.border}`, background: active ? `${C.aqua}14` : "transparent", color: active ? C.aqua : C.muted, transition: "all 0.15s", fontFamily: "'Inter',sans-serif" }}>
                {active && <CheckCircle2 size={13} color={C.aqua} />}
                {cat}
              </button>
            );
          })}
        </div>
        <p style={{ fontSize: 11, color: C.muted, marginTop: 14 }}>{activeCats.length} of {CATEGORIES.length} categories active · changes apply on next scheduled run</p>
      </Card>

      <Card style={{ padding: 24, marginBottom: 14 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: C.text, margin: "0 0 4px" }}>Data Source Status</h3>
        <p style={{ fontSize: 12, color: C.muted, margin: "0 0 16px" }}>Scraping configuration and last-run metadata per platform.</p>
        <div style={{ display: "grid", gap: 12 }}>
          {sources.map((src: any, i: number) => (
            <div key={i} style={{ padding: 16, border: `1px solid ${C.border}`, borderRadius: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: C.success, display: "inline-block" }} />
                  <span style={{ fontSize: 14, fontWeight: 700, color: C.text }}>{src.platform}</span>
                </div>
                <Badge variant="success">{src.status}</Badge>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
                <div>
                  <p style={{ fontSize: 10, color: C.muted, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 4px" }}>Last Scraped</p>
                  <p style={{ fontSize: 12, color: C.text, fontFamily: MONO, margin: 0 }}>{fmt(src.last_scraped)}</p>
                </div>
                <div>
                  <p style={{ fontSize: 10, color: C.muted, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 4px" }}>Next Scheduled Run</p>
                  <p style={{ fontSize: 12, color: C.text, fontFamily: MONO, margin: 0 }}>Not scheduled</p>
                </div>
                <div>
                  <p style={{ fontSize: 10, color: C.muted, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 4px" }}>Products Indexed</p>
                  <p style={{ fontSize: 22, fontWeight: 800, fontFamily: MONO, color: C.aqua, margin: 0 }}>{(src.products_indexed ?? 0).toLocaleString()}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card style={{ padding: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: C.text, margin: "0 0 4px" }}>ETL Health</h3>
        <p style={{ fontSize: 12, color: C.muted, margin: "0 0 4px" }}>Last 10 pipeline runs from etl_run_log.</p>
        {lastUpdated && (
          <p style={{ fontSize: 11, color: C.muted, margin: "0 0 16px", fontFamily: MONO }}>Data refreshed: {fmt(lastUpdated)}</p>
        )}
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                {["Run ID", "Timestamp", "Records", "Inserted", "Duplicates", "Errors"].map(h => (
                  <th key={h} style={{ padding: "7px 10px", textAlign: "left", color: C.muted, fontWeight: 500, fontSize: 10, letterSpacing: "0.05em", textTransform: "uppercase", whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {etlRuns.length === 0 ? (
                <tr><td colSpan={6} style={{ padding: "20px 10px", color: C.muted, textAlign: "center", fontSize: 12 }}>No ETL runs recorded.</td></tr>
              ) : etlRuns.map((run: any, i: number) => (
                <tr key={i} style={{ borderBottom: `1px solid ${C.border}18` }}>
                  <td style={{ padding: "8px 10px", color: C.muted, fontFamily: MONO }}>{run.run_id}</td>
                  <td style={{ padding: "8px 10px", color: C.text, fontFamily: MONO, whiteSpace: "nowrap" }}>{fmt(run.run_timestamp)}</td>
                  <td style={{ padding: "8px 10px", color: C.text, fontFamily: MONO }}>{(run.records_processed ?? 0).toLocaleString()}</td>
                  <td style={{ padding: "8px 10px", color: C.text, fontFamily: MONO }}>{(run.rows_inserted ?? 0).toLocaleString()}</td>
                  <td style={{ padding: "8px 10px", color: run.duplicates_removed > 0 ? C.warning : C.muted, fontFamily: MONO }}>{run.duplicates_removed ?? 0}</td>
                  <td style={{ padding: "8px 10px", color: run.errors > 0 ? C.danger : C.success, fontFamily: MONO }}>{run.errors ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Root App
══════════════════════════════════════════════════════════════════════════════ */
const PAGE_TITLES: Record<string, string> = {
  overview:      "Overview",
  crossplatform: "Cross-Platform Analysis",
  statistics:    "Statistics",
  sentiment:     "Sentiment (Proxy)",
  catalogue:     "Product Catalogue",
  pipeline:      "Pipeline Health",
  settings:      "Settings",
};

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activePage, setActivePage]   = useState("overview");
  const [dashData, setDashData]       = useState<any>(null);
  const [loading, setLoading]         = useState(true);
  const [fetchError, setFetchError]   = useState<string | null>(null);

  // ── Global filter state ──────────────────────────────────────────────────
  const [filters, setFilters] = useState<Filters>({
    categories: [],
    platforms:  [],
    brands:     [],
    search:     "",
  });

  useEffect(() => {
    fetch("/frontend_data.json")
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(json => { setDashData(json); setLoading(false); })
      .catch(err => { setFetchError(String(err)); setLoading(false); });
  }, []);

  // ── Derive option lists from raw products ────────────────────────────────
  const allProducts: any[] = dashData?.products ?? [];

  const allCats = useMemo(
    () => [...new Set(allProducts.map((p: any) => p.cat ?? p.category ?? ""))].filter(Boolean).sort() as string[],
    [allProducts]
  );
  const allBrands = useMemo(
    () => [...new Set(allProducts.map((p: any) => p.brand ?? ""))].filter(Boolean).sort() as string[],
    [allProducts]
  );

  // ── filteredProducts ─────────────────────────────────────────────────────
  // Products shape: { cat, brand, avail ("amazon"|"flipkart"|"both"), amazon?, flipkart? }
  const filteredProducts = useMemo(() => {
    return allProducts.filter((p: any) => {
      const cat   = (p.cat ?? p.category ?? "") as string;
      const brand = (p.brand ?? "") as string;
      const avail = (p.avail ?? "") as string; // "amazon" | "flipkart" | "both"
      const name  = (p.name ?? "") as string;

      const catOk = !filters.categories.length ||
        filters.categories.includes(cat);

      const platOk = !filters.platforms.length ||
        filters.platforms.some(pl => {
          if (pl === "Amazon")   return avail === "amazon"   || avail === "both";
          if (pl === "Flipkart") return avail === "flipkart" || avail === "both";
          return false;
        });

      const brandOk = !filters.brands.length ||
        filters.brands.includes(brand);

      const searchOk = !filters.search ||
        name.toLowerCase().includes(filters.search.toLowerCase()) ||
        brand.toLowerCase().includes(filters.search.toLowerCase());

      return catOk && platOk && brandOk && searchOk;
    });
  }, [allProducts, filters]);

  if (loading) return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: C.bg, color: C.muted, fontFamily: "'Inter',system-ui,sans-serif", flexDirection: "column", gap: 12 }}>
      <svg width="24" height="14" viewBox="0 0 24 14" fill="none" style={{ opacity: 0.6 }}>
        <polyline points="0,7 3,7 5,1 8,13 11,4 13,10 15.5,7 19,7 24,7" stroke="#6EC6CA" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span style={{ fontSize: 13 }}>Loading MarketPulse data…</span>
    </div>
  );

  if (fetchError) return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: C.bg, color: "#F87171", fontFamily: "'Inter',system-ui,sans-serif", flexDirection: "column", gap: 8 }}>
      <span style={{ fontSize: 14, fontWeight: 600 }}>Failed to load data</span>
      <span style={{ fontSize: 12, color: "#7A8599" }}>{fetchError}</span>
      <span style={{ fontSize: 11, color: "#7A8599" }}>Run <code style={{ background: "#1A2235", padding: "2px 6px", borderRadius: 4 }}>python export_data.py</code> and refresh.</span>
    </div>
  );

  const d = dashData ?? {};
  const hasFilters = filters.categories.length > 0 || filters.platforms.length > 0 || filters.brands.length > 0;

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: C.bg, color: C.text, fontFamily: "'Inter',system-ui,sans-serif" }}>
      <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen(o => !o)} active={activePage} onNav={setActivePage} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <TopBar
          filters={filters}
          allCats={allCats}
          allBrands={allBrands}
          onChange={setFilters}
          lastSync={fmt(d.pipeline_health?.last_updated ?? "")}
        />
        {hasFilters && activePage !== "pipeline" && activePage !== "settings" && (
          <FilterPills filters={filters} onChange={setFilters} />
        )}
        <div style={{ borderBottom: `1px solid ${C.border}`, padding: "11px 24px", flexShrink: 0, background: C.bg }}>
          <h1 style={{ fontSize: 17, fontWeight: 800, color: C.text, margin: 0, letterSpacing: "-0.02em" }}>{PAGE_TITLES[activePage]}</h1>
        </div>
        <main style={{ flex: 1, overflowY: "auto", padding: 22 }}>
          {activePage === "overview"      && <OverviewScreen      data={d} filteredProducts={filteredProducts} />}
          {activePage === "crossplatform" && <CrossPlatformScreen data={d} filteredProducts={filteredProducts} />}
          {activePage === "statistics"    && <StatisticsScreen    data={d} filteredProducts={filteredProducts} />}
          {activePage === "sentiment"     && <SentimentScreen     data={d} filteredProducts={filteredProducts} />}
          {activePage === "catalogue"     && <CatalogueScreen     data={d} filteredProducts={filteredProducts} />}
          {activePage === "pipeline"      && <PipelineScreen      data={d} />}
          {activePage === "settings"      && <SettingsScreen      data={d} />}
        </main>
      </div>
    </div>
  );
}

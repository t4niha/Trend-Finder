import { Link, createFileRoute } from "@tanstack/react-router";
import { ArrowLeft, ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchTrends, getNicheLabel, type Trend, type WeekResult } from "@/lib/trend-api";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/explore/$niche/$weekNumber")({
  codeSplitGroupings: [],
  head: ({ params }) => ({
    meta: [
      { title: `${getNicheLabel(params.niche)} Trends — Reddit Trend Finder` },
      { name: "description", content: `Top 3 Reddit trends for r/${params.niche}.` },
      { property: "og:title", content: `${getNicheLabel(params.niche)} Trends — Reddit Trend Finder` },
      { property: "og:description", content: `Top 3 Reddit trends for r/${params.niche}.` },
    ],
  }),
  component: TrendResultsPage,
});

function TrendResultsPage() {
  const { niche, weekNumber } = Route.useParams();
  const [week, setWeek] = useState<WeekResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    async function loadTrends() {
      try {
        setLoading(true);
        const payload = await fetchTrends(niche, weekNumber, controller.signal);
        setWeek(payload.results?.[0] ?? null);
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          toast.error("Could not load trend results", { description: "The API request failed. Please try again." });
        }
      } finally {
        setLoading(false);
      }
    }
    loadTrends();
    return () => controller.abort();
  }, [niche, weekNumber]);

  const breadcrumbWeek = week?.week_label ?? "Selected timeframe";

  return (
    <main className="min-h-screen bg-background px-5 py-8 text-foreground">
      <section className="mx-auto max-w-5xl animate-in fade-in slide-in-from-bottom-4 duration-500">
        <nav className="flex flex-wrap items-center gap-2 pt-4 text-sm text-muted-foreground">
          <Link to="/" className="transition hover:text-primary">Home</Link>
          <ChevronRight className="size-4" />
          <Link to="/explore/$niche" params={{ niche }} className="transition hover:text-primary">{getNicheLabel(niche)}</Link>
          <ChevronRight className="size-4" />
          <span className="text-foreground">{breadcrumbWeek}</span>
        </nav>

        <div className="mb-8 mt-8 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-normal text-primary">Step 3 of 3</p>
            <h1 className="mt-3 font-display text-4xl font-bold sm:text-6xl">Trend Results</h1>
          </div>
          <Button asChild variant="chip">
            <Link to="/explore/$niche" params={{ niche }}>
              <ArrowLeft className="size-4" />
              Back to Timeframes
            </Link>
          </Button>
        </div>

        {loading ? <ResultsLoading /> : week ? <ResultsContent week={week} /> : <EmptyResults niche={niche} />}
      </section>
    </main>
  );
}

function ResultsLoading() {
  return (
    <div className="space-y-5">
      <div className="glass-panel relative overflow-hidden rounded-lg border border-border p-6">
        <div className="loading-scan absolute inset-y-0 left-0 w-1/2" />
        <p className="mb-5 text-sm font-medium text-primary">Analyzing clusters...</p>
        <Skeleton className="mb-4 h-9 w-72 max-w-full" />
        <div className="grid gap-3 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-16" />)}
        </div>
      </div>
      {Array.from({ length: 3 }).map((_, index) => (
        <div key={index} className="glass-panel rounded-lg border border-border p-6">
          <Skeleton className="mb-4 h-7 w-3/4" />
          <Skeleton className="mb-3 h-5 w-full" />
          <Skeleton className="mb-5 h-5 w-5/6" />
          <div className="flex gap-2"><Skeleton className="h-7 w-20" /><Skeleton className="h-7 w-24" /><Skeleton className="h-7 w-16" /></div>
        </div>
      ))}
    </div>
  );
}

function ResultsContent({ week }: { week: WeekResult }) {
  return (
    <div className="space-y-5">
      <header className="glass-panel rounded-lg border border-border p-6">
        <h2 className="text-3xl font-bold text-foreground">{week.week_label}</h2>
        <div className="mt-5 grid gap-3 sm:grid-cols-4">
          <SummaryStat label="Posts" value={week.post_count.toLocaleString()} />
          <SummaryStat label="Clusters" value={String(week.clusters_found)} />
          <SummaryStat label="Noise posts" value={String(week.noise_posts)} />
          <SummaryStat label="Top trends" value={String(week.trends.length)} />
        </div>
      </header>
      <div className="space-y-4">
        {week.trends.slice(0, 3).map((trend) => <TrendCard key={`${trend.rank}-${trend.title}`} trend={trend} />)}
      </div>
    </div>
  );
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-secondary p-4">
      <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-bold text-foreground">{value}</p>
    </div>
  );
}

function TrendCard({ trend }: { trend: Trend }) {
  const [open, setOpen] = useState(false);
  const entities = useMemo(() => trend.key_entities ?? {}, [trend.key_entities]);
  const sentiment = trend.sentiment?.toLowerCase() ?? "mixed";

  return (
    <article className="glass-panel rounded-lg border border-border p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          <span className="rounded-md bg-primary px-3 py-1.5 text-sm font-bold text-primary-foreground">#{trend.rank}</span>
          <div>
            <h3 className="text-2xl font-bold text-foreground">{trend.title}</h3>
            <SentimentBadge sentiment={sentiment} />
          </div>
        </div>
      </div>
      <p className="mt-5 leading-7 text-muted-foreground">{trend.description}</p>
      <div className="mt-5 space-y-3">
        <EntityGroup label="Companies" items={entities.companies} className="border-chart-4/40 bg-chart-4/10 text-chart-4" />
        <EntityGroup label="Products" items={entities.products} className="border-chart-3/40 bg-chart-3/10 text-chart-3" />
        <EntityGroup label="People" items={entities.people} className="border-positive/40 bg-positive/10 text-positive" />
      </div>
      {trend.importance && (
        <div className="mt-5 rounded-lg border border-accent/30 bg-accent/10 p-4">
          <p className="text-sm font-semibold text-accent">Importance</p>
          <p className="mt-2 leading-7 text-foreground">{trend.importance}</p>
        </div>
      )}
      {!!trend.references?.length && (
        <div className="mt-5 border-t border-border pt-4">
          <button onClick={() => setOpen((value) => !value)} className="flex items-center gap-2 text-sm font-semibold text-primary transition hover:text-foreground">
            <ChevronDown className={cn("size-4 transition", open && "rotate-180")} />
            References
          </button>
          {open && (
            <div className="mt-3 space-y-2 animate-in fade-in slide-in-from-top-2 duration-200">
              {trend.references.map((reference) => (
                <a key={reference} href={reference} target="_blank" rel="noreferrer" className="flex items-center gap-2 break-all text-sm text-muted-foreground transition hover:text-primary">
                  <ExternalLink className="size-4 shrink-0" />
                  {reference}
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </article>
  );
}

function SentimentBadge({ sentiment }: { sentiment: string }) {
  const className = sentiment === "positive" ? "border-positive/40 bg-positive/10 text-positive" : sentiment === "negative" ? "border-negative/40 bg-negative/10 text-negative" : "border-mixed/40 bg-mixed/10 text-mixed";
  return <span className={cn("mt-3 inline-flex rounded-md border px-2.5 py-1 text-xs font-bold uppercase tracking-normal", className)}>{sentiment}</span>;
}

function EntityGroup({ label, items, className }: { label: string; items?: string[]; className: string }) {
  if (!items?.length) return null;
  return (
    <div>
      <p className="mb-2 text-xs font-medium uppercase tracking-normal text-muted-foreground">{label}</p>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => <span key={item} className={cn("rounded-md border px-2.5 py-1 text-sm font-semibold", className)}>{item}</span>)}
      </div>
    </div>
  );
}

function EmptyResults({ niche }: { niche: string }) {
  return <div className="rounded-lg border border-border bg-surface p-8 text-muted-foreground">No trends found for r/{niche} in this timeframe.</div>;
}

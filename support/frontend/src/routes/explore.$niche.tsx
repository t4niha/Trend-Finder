import { Link, Outlet, createFileRoute, useLocation } from "@tanstack/react-router";
import { ArrowLeft, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchTrends, getNicheLabel, type WeekResult } from "@/lib/trend-api";

export const Route = createFileRoute("/explore/$niche")({
  codeSplitGroupings: [],
  head: ({ params }) => ({
    meta: [
      { title: `${getNicheLabel(params.niche)} Timeframes — Reddit Trend Finder` },
      { name: "description", content: `Pick a week to see the top 3 trending topics in r/${params.niche}.` },
      { property: "og:title", content: `${getNicheLabel(params.niche)} Timeframes — Reddit Trend Finder` },
      { property: "og:description", content: `Pick a week to see the top 3 trending topics in r/${params.niche}.` },
    ],
  }),
  component: TimeframePage,
});

function TimeframePage() {
  const { niche } = Route.useParams();
  const location = useLocation();
  const [weeks, setWeeks] = useState<WeekResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    async function loadWeeks() {
      try {
        setLoading(true);
        const payload = await fetchTrends(niche, undefined, controller.signal);
        setWeeks(payload.results ?? []);
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          toast.error("Could not load timeframes", { description: "Check the API connection and try again." });
        }
      } finally {
        setLoading(false);
      }
    }
    loadWeeks();
    return () => controller.abort();
  }, [niche]);

  if (location.pathname !== `/explore/${niche}`) {
    return <Outlet />;
  }

  return (
    <main className="min-h-screen bg-background px-5 py-8 text-foreground">
      <section className="mx-auto max-w-5xl animate-in fade-in slide-in-from-bottom-4 duration-500">
        <nav className="flex items-center gap-2 pt-4 text-sm text-muted-foreground">
          <Link to="/" className="transition hover:text-primary">Home</Link>
          <ChevronRight className="size-4" />
          <span className="text-foreground">{getNicheLabel(niche)}</span>
        </nav>

        <div className="mb-10 mt-8 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-normal text-primary">Step 2 of 3</p>
            <h1 className="mt-3 font-display text-4xl font-bold sm:text-6xl">Select a Timeframe</h1>
            <p className="mt-4 text-lg text-muted-foreground">
              Pick a week to see the top 3 trending topics in r/{niche}
            </p>
          </div>
          <Button asChild variant="chip">
            <Link to="/explore">
              <ArrowLeft className="size-4" />
              Back to Niches
            </Link>
          </Button>
        </div>

        {loading ? (
          <div className="grid gap-4 md:grid-cols-2">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="glass-panel rounded-lg border border-border p-6">
                <Skeleton className="mb-5 h-8 w-64 max-w-full" />
                <div className="flex gap-3">
                  <Skeleton className="h-5 w-24" />
                  <Skeleton className="h-5 w-28" />
                </div>
              </div>
            ))}
          </div>
        ) : weeks.length ? (
          <div className="grid gap-4 md:grid-cols-2">
            {weeks.map((week) => (
              <Link
                key={week.week_number}
                to="/explore/$niche/$weekNumber"
                params={{ niche, weekNumber: String(week.week_number) }}
                className="group glass-panel rounded-lg border border-border p-6 transition duration-300 hover:-translate-y-1 hover:border-primary/60"
              >
                <div className="flex items-start justify-between gap-4">
                  <h2 className="text-2xl font-bold text-foreground">{week.week_label}</h2>
                  <ChevronRight className="mt-1 size-5 text-muted-foreground transition group-hover:translate-x-1 group-hover:text-primary" />
                </div>
                <div className="mt-5 flex flex-wrap gap-3 text-sm text-muted-foreground">
                  <span className="rounded-md border border-border bg-secondary px-3 py-1">{week.post_count.toLocaleString()} posts</span>
                  <span className="rounded-md border border-border bg-secondary px-3 py-1">{week.clusters_found} clusters</span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-border bg-surface p-8 text-muted-foreground">
            No timeframes found for r/{niche}.
          </div>
        )}
      </section>
    </main>
  );
}

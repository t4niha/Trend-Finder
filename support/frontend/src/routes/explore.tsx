import { Link, Outlet, createFileRoute, useLocation } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Skeleton } from "@/components/ui/skeleton";
import { fetchNiches, getNicheLabel, nicheMeta, type NicheSummary } from "@/lib/trend-api";

export const Route = createFileRoute("/explore")({
  codeSplitGroupings: [],
  head: () => ({
    meta: [
      { title: "Select a Niche — Reddit Trend Finder" },
      { name: "description", content: "Choose a Reddit community to explore trending topics." },
      { property: "og:title", content: "Select a Niche — Reddit Trend Finder" },
      { property: "og:description", content: "Choose a Reddit community to explore trending topics." },
    ],
  }),
  component: ExplorePage,
});

function ExplorePage() {
  const location = useLocation();
  const [niches, setNiches] = useState<NicheSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    async function loadNiches() {
      try {
        setLoading(true);
        const payload = await fetchNiches(controller.signal);
        setNiches(payload.niches.slice(0, 6));
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          toast.error("Could not load niches", { description: "Make sure the API is running at http://localhost:8000." });
        }
      } finally {
        setLoading(false);
      }
    }
    loadNiches();
    return () => controller.abort();
  }, []);

  if (location.pathname !== "/explore") {
    return <Outlet />;
  }

  return (
    <main className="min-h-screen bg-background px-5 py-8 text-foreground">
      <section className="mx-auto max-w-6xl animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="mb-10 pt-8">
          <p className="text-sm font-medium uppercase tracking-normal text-primary">Step 1 of 3</p>
          <h1 className="mt-3 font-display text-4xl font-bold sm:text-6xl">Select a Niche</h1>
          <p className="mt-4 text-lg text-muted-foreground">Choose a Reddit community to explore trending topics</p>
        </div>

        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="glass-panel rounded-lg border border-border p-6">
                <Skeleton className="mb-5 h-12 w-12 rounded-lg" />
                <Skeleton className="mb-3 h-7 w-40" />
                <Skeleton className="h-5 w-28" />
              </div>
            ))}
          </div>
        ) : niches.length ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {niches.map((item) => (
              <Link
                key={item.niche}
                to="/explore/$niche"
                params={{ niche: item.niche }}
                className="group glass-panel rounded-lg border border-border p-6 transition duration-300 hover:-translate-y-1 hover:border-primary/60"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="text-5xl" aria-hidden="true">
                    {nicheMeta[item.niche]?.emoji ?? "📡"}
                  </div>
                  <ArrowRight className="mt-2 size-5 text-muted-foreground transition group-hover:translate-x-1 group-hover:text-primary" />
                </div>
                <h2 className="mt-6 text-2xl font-bold text-foreground">{getNicheLabel(item.niche)}</h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  {item.total_posts.toLocaleString()} posts analyzed
                </p>
              </Link>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-border bg-surface p-8 text-muted-foreground">
            No niches found. Start the API at http://localhost:8000 and refresh this page.
          </div>
        )}
      </section>
    </main>
  );
}

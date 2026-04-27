import { Link, createFileRoute } from "@tanstack/react-router";
import { ArrowRight, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/")({
  codeSplitGroupings: [],
  head: () => ({
    meta: [
      { title: "Reddit Trend Finder" },
      {
        name: "description",
        content: "AI-powered trend intelligence dashboard for discovering Reddit niche trends.",
      },
      { property: "og:title", content: "Reddit Trend Finder" },
      {
        property: "og:description",
        content: "Explore AI-powered trend intelligence from Reddit through a guided dashboard.",
      },
    ],
  }),
  component: WelcomePage,
});

function WelcomePage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-background px-5 py-8 text-foreground">
      <section className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl flex-col justify-center py-12">
        <div className="max-w-3xl animate-in fade-in slide-in-from-bottom-6 duration-700">
          <div className="mb-8 inline-flex items-center gap-2 rounded-md border border-primary/30 bg-primary/10 px-3 py-1.5 text-sm font-medium text-primary">
            <Sparkles className="size-4" />
            Live Reddit intelligence
          </div>
          <h1 className="font-display text-5xl font-bold leading-tight text-balance text-foreground sm:text-7xl lg:text-8xl">
            Reddit Trend Finder
          </h1>
          <p className="mt-6 text-2xl font-semibold text-primary sm:text-3xl">
            AI-powered trend intelligence from Reddit
          </p>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-muted-foreground">
            Discover the top 3 trending topics in a niche and timeframe through clustered Reddit conversations.
          </p>
          <div className="mt-10">
            <Button asChild variant="signal" size="lg" className="h-12 px-6 text-base">
              <Link to="/explore">
                Explore Trends
                <ArrowRight className="size-5" />
              </Link>
            </Button>
          </div>
        </div>
      </section>
    </main>
  );
}

# Reddit Trend Finder

A modern dark-themed React dashboard for exploring AI-powered trend intelligence from Reddit. The frontend connects to a REST API running at `http://localhost:8000` and guides users through niche selection, timeframe selection, trend results, and trend details.

## Prerequisites

Before running the frontend, make sure you have:

- Node.js installed
- npm installed
- The backend API running at `http://localhost:8000`

## Installation

From the `frontend` directory, install dependencies:

```bash
npm install
```

## Run the Development Server

Start the frontend locally:

```bash
npm run dev
```

The app will usually be available at:

```text
http://localhost:8080
```

If Vite chooses a different port, use the URL shown in the terminal.

## Backend API

This frontend expects the backend REST API to be running at:

```text
http://localhost:8000
```

Start the backend first, then start the frontend.

## Available Scripts

```bash
npm run dev
```

Runs the app in development mode.

```bash
npm run build
```

Builds the app for production.

```bash
npm run preview
```

Previews the production build locally.

```bash
npm run lint
```

Runs ESLint checks.

```bash
npm run format
```

Formats the code with Prettier.

## Project Structure

```text
frontend/
├── src/
│   ├── components/        # Reusable UI components
│   ├── hooks/             # Custom React hooks
│   ├── lib/               # API helpers and utilities
│   ├── routes/            # App pages and routes
│   ├── route.tsx          # Route setup file
│   ├── routeTree.gen.ts   # Auto-generated route tree
│   └── styles.css         # Global Tailwind CSS styles
├── .env                   # Environment variables, for example VITE_API_BASE_URL
├── .gitignore             # Git ignored files
├── .prettierignore        # Prettier ignored files
├── .prettierrc            # Prettier formatting config
├── bun.lockb              # Bun lock file
├── bunfig.toml            # Bun config
├── components.json        # UI component config
├── eslint.config.js       # ESLint config
├── package.json           # Dependencies and npm scripts
├── package-lock.json      # npm lock file
├── tsconfig.json          # TypeScript configuration
├── vite.config.ts         # Vite configuration
└── README.md              # Frontend setup instructions
```


## Main Pages

- `/` — Welcome page
- `/explore` — Niche selection
- `/explore/:niche` — Timeframe selection
- `/explore/:niche/:weekNumber` — Trend results and details
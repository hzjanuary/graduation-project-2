# Enterprise Multi-Agent OS Frontend

Next.js dashboard foundation for Enterprise Multi-Agent OS.

This frontend is currently a SPEC-009 bootstrap only. It provides the project
structure, TypeScript, Tailwind CSS, and shadcn/ui-compatible conventions for
the future dashboard. It does not call backend APIs, implement authentication,
render workflow business data, or connect to the workflow event WebSocket yet.

## Requirements

- Node.js 20 or later
- npm

## Environment

Copy the example environment file:

```bash
cp .env.example .env.local
```

Configured variables:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000/api/v1
```

Do not put secrets in `NEXT_PUBLIC_*` variables. They are exposed to the
browser by design.

## Install

```bash
npm install
```

## Development

```bash
npm run dev
```

The app starts at:

```text
http://localhost:3000
```

## Quality Checks

```bash
npm run lint
npm run typecheck
npm run build
```

## Current Scope

Implemented in TASK 009.1:

- Next.js App Router foundation
- TypeScript configuration
- Tailwind CSS configuration
- shadcn/ui-compatible `components/ui` and `lib/utils.ts` structure
- Static placeholder dashboard shell

Deferred to later SPEC-009 tasks:

- Auth/session logic
- Backend API client
- Workflow list/detail/create/run UI
- WebSocket event timeline
- Full dashboard navigation

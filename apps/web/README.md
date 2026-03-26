# apps/web — Frontend Web App

This is the frontend web application for the product, built with **React + TypeScript**.

---

## Prerequisites

- Node.js >= 20
- npm >= 10

---

## Getting Started

```bash
cd apps/web
cp .env.example .env.local     # Set frontend env vars
npm install
npm run dev                    # Starts on http://localhost:3000
```

---

## Folder Structure

```
src/
├── components/     ← Reusable UI components (buttons, forms, modals, tables)
├── pages/          ← Page-level views — one folder per route/feature
├── hooks/          ← Custom React hooks (data fetching, auth, state)
└── lib/            ← API clients, utility functions, constants, types
```

### Conventions

| Folder | Naming | Example |
|--------|--------|---------|
| `components/` | PascalCase | `Button.tsx`, `DataTable.tsx` |
| `pages/` | kebab-case dirs | `pages/dashboard/index.tsx` |
| `hooks/` | camelCase, `use` prefix | `useFeatureList.ts` |
| `lib/` | camelCase | `apiClient.ts`, `formatDate.ts` |

---

## Running Tests

```bash
npm test                    # Unit tests (Vitest)
npm run test:coverage       # With coverage report
```

---

## Building for Production

```bash
npm run build
npm run start
```

---

## Environment Variables

Copy `.env.example` to `.env.local` and set values:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

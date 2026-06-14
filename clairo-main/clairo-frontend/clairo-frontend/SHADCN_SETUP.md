# shadcn / Tailwind / TypeScript setup (Clairo)

This project is configured for the **shadcn/ui** workflow on **Vite + React**.

## What is already configured

| Piece | Location |
|--------|----------|
| shadcn config | `components.json` |
| UI components | `src/components/ui/` |
| Utilities (`cn`) | `src/lib/utils.ts` |
| Global styles + Tailwind | `src/index.css` (`@import "tailwindcss"`) |
| Path alias `@/*` | `vite.config.ts`, `tsconfig.app.json` |
| TypeScript | `tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json` |

## Default paths (from `components.json`)

- **Components:** `@/components` → `src/components`
- **UI primitives:** `@/components/ui` → `src/components/ui` ← **required for shadcn CLI**
- **Utils:** `@/lib/utils` → `src/lib/utils.ts`
- **Styles:** `src/index.css`

### Why `src/components/ui` matters

The shadcn CLI installs every component into `components/ui` by default. Keeping this folder:

- Matches official docs and `npx shadcn@latest add …` behavior
- Avoids duplicate or scattered UI primitives
- Lets you import consistently: `import { Button } from "@/components/ui/button"`

## Add more shadcn components

From `clairo-frontend/`:

```bash
npx shadcn@latest init   # only if components.json is missing
npx shadcn@latest add button textarea card
```

## Shader component

Official shader lives at:

`src/components/ui/shader-animation.tsx`

Used by `ShaderHero`:

```tsx
import { ShaderAnimation } from "@/components/ui/shader-animation";
```

## Dependencies

```bash
npm install three lucide-react clsx tailwind-merge class-variance-authority
npm install -D typescript @types/node tailwindcss @tailwindcss/vite
```

## Scripts

```bash
npm run dev      # Vite dev server
npm run build    # Production build
npm run typecheck  # tsc --noEmit (if added)
```

## Migrating remaining `.jsx` to `.tsx`

Existing feature components can stay `.jsx` (`allowJs: true`). New shadcn components should be `.tsx` under `src/components/ui/`.

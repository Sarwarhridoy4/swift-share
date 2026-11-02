# SwiftShare Frontend

React 19 SPA built with Vite and Tailwind CSS v4. Builds production assets into `../static/` for serving by the FastAPI backend.

## Scripts

| Script                  | Description                                |
|-------------------------|--------------------------------------------|
| `bun install`           | Install dependencies                       |
| `bun run dev`           | Start Vite dev server (port 5173)          |
| `bun run build`         | Build production assets into `../static/`  |

## Project Structure

```
frontend/
├── index.html            # Vite HTML entry
├── vite.config.ts        # Vite config (base: /static/, outDir: ../static/)
├── postcss.config.js     # Tailwind CSS PostCSS plugin
├── package.json
├── bun.lockb
├── tsconfig.json
└── src/
    ├── main.tsx          # React entry point
    ├── index.css         # Tailwind CSS source
    ├── App.tsx           # Root component
    ├── lib/utils.ts      # Format helpers, file icons
    ├── types.ts          # TypeScript types
    ├── components/       # React components
    │   ├── App.tsx (via src/App.tsx)
    │   ├── Breadcrumb.tsx
    │   ├── ConfirmModal.tsx
    │   ├── ContextMenu.tsx
    │   ├── FileBrowser.tsx
    │   ├── FileItem.tsx
    │   ├── Header.tsx
    │   ├── NewFolderModal.tsx
    │   ├── PreviewModal.tsx
    │   ├── QRModal.tsx
    │   ├── ShareModal.tsx
    │   ├── StatsBar.tsx
    │   ├── ToastContainer.tsx
    │   ├── Toolbar.tsx
    │   └── TransferPanel.tsx
```

## Tech Stack

- React 19
- Vite 8
- Tailwind CSS v4 (via `@tailwindcss/postcss`)
- Socket.IO client 4
- lucide-react icons
- TypeScript

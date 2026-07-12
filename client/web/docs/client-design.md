# Perseus Client Design Document

## Overview

Perseus is a self-hosted Git collaborative development platform. The client is a React SPA that provides code hosting, real-time collaboration, team chat, code review, and project management in a unified interface.

## Tech Stack

| Category | Choice | Rationale |
|----------|--------|-----------|
| Framework | React 19 + TypeScript 6 | Latest stable, compiler-ready |
| Build | Vite 8 | Fast dev server, native TS support |
| UI Library | Ant Design 5 | Enterprise component library, consistent design system |
| Icons | @ant-design/icons | Sufficient for all use cases (includes GitHub/GitLab icons) |
| Routing | React Router v7 | Industry standard, layout routes, loaders |
| State | Zustand | Lightweight global state for WebSocket, auth, presence |
| Forms | React Hook Form | Performant, minimal re-renders, Zod integration |
| Editor | CodeMirror 6 | Extensible, lightweight, suitable for collaborative editing |
| Lint | ESlint | Fast JavaScript/TypeScript-based linter |
| Animation | React Spring | Simple, performant animation library |

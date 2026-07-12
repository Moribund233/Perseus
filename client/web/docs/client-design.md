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
| Lint | Oxlint | Fast Rust-based linter |

## Pages & Routes

```
/public            → Landing page (separate HTML, not React)
/auth/login        → Sign In page
/auth/register     → Create Account page
/app               → Authenticated application shell
  /app/dashboard   → Dashboard (landing after login)
  /app/repos       → Repository list
  /app/repos/:id   → Repository detail (code browser, file tree, README)
  /app/repos/:id/tree/:ref/* → File tree browsing
  /app/repos/:id/blob/:ref/* → File content view
  /app/repos/:id/commits       → Commit history
  /app/repos/:id/pull-requests → PR list
  /app/repos/:id/pull-requests/:number → PR detail (conversation/commits/files)
  /app/repos/:id/issues        → Issue list
  /app/repos/:id/issues/:number → Issue detail
  /app/repos/:id/settings      → Repository settings
  /app/editor/:repoId          → Online code editor (collaborative)
    ?file=path                 → Open specific file
    ?ref=branch                → Branch ref
  /app/chat                    → Team chat
  /app/chat/:channel           → Specific channel/DM
  /app/settings                → User settings
```

## Auth Flow

1. **Landing page** (`public/landing.html`) — Product marketing, click "Sign In" or "Get Started"
2. **Auth modal** (embedded in landing) — Login / Register with tab switching
   - OAuth buttons: GitHub, GitLab
   - Email/password form with validation
3. **On success** — Redirect to `/app/dashboard`
4. **JWT tokens**: Access token (short-lived) + Refresh token (stored in httpOnly cookie)
5. **Zustand auth store**: `useAuthStore` — manages token, user profile, login/logout actions

## Layout Structure

```
┌─────────────────────────────────────────────┐
│  AppShell                                   │
│  ┌──────┬──────────────────────────────────┐│
│  │      │  TopBar                          ││
│  │ Side │  - Breadcrumb                    ││
│  │ bar  │  - Search (Ctrl+K)               ││
│  │      │  - Notifications (bell)          ││
│  │      │  - User avatar dropdown          ││
│  │      ├──────────────────────────────────┤│
│  │      │  <Outlet /> (page content)       ││
│  │      │                                  ││
│  │      │                                  ││
│  │      │                                  ││
│  │      │                                  ││
│  └──────┴──────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

- **Sidebar**: Collapsible (64px / 240px), nav icons + labels, active indicator
- **TopBar**: Breadcrumb, global search, notification bell, user menu
- **Content**: Route-driven `<Outlet />`

## Component Tree (key pages)

### Dashboard
```
DashboardPage
├── WelcomeBanner (greeting + stats)
├── StatsGrid (repos, PRs, members, commits)
├── ActivityFeed (recent events)
└── QuickRepos (favorite repositories)
```

### Repository Browser
```
RepoDetailPage
├── RepoHeader (name, visibility, actions: Watch/Star/Fork)
├── RepoTabs (Code / Issues / Pull Requests / Settings)
├── FileExplorer
│   ├── FileTree (sidebar, collapsible)
│   └── FileContent / README (main area)
└── CommitHistory (for Code tab)
```

### Pull Request
```
PRDetailPage
├── PRHeader (title, status, metadata)
├── PRTabs (Conversation / Commits / Files Changed)
├── ConversationTab
│   ├── PRDescription
│   └── CommentThread[] (inline replies)
├── FilesChangedTab
│   ├── FileDiff[] (unified diff view)
│   └── InlineComment[] (line-attached discussions)
└── PRMergeBox (merge button, method selector)
```

### Code Editor (collaborative)
```
CollaborativeEditorPage
├── EditorSidebar (file tree)
├── EditorMain
│   ├── EditorTabs (open files)
│   ├── EditorBreadcrumb
│   ├── CollabBar (connection status, online avatars, viewer count)
│   ├── CodeMirror6
│   │   ├── DiscussionGutter (💬 markers)
│   │   └── CollabCursors (remote cursor overlays)
│   ├── CollabPanel (bottom)
│   │   ├── DiscussionsTab (threads linked to lines)
│   │   └── EditorsTab (who's online, what file)
│   └── StatusBar (branch, connection, position, online count)
└── WebSocketManager (Zustand store)
    ├── Connection lifecycle (connect/disconnect/reconnect)
    ├── Operation sync (CRDT operations)
    ├── Presence sync (cursors, selections)
    └── Heartbeat
```

### Team Chat
```
ChatPage
├── ChannelList (sidebar)
│   ├── Channels (general, engineering, etc.)
│   └── DirectMessages (user list with online status)
├── ChatMain
│   ├── ChatHeader (channel name, topic, member count)
│   ├── MessageList
│   │   └── Message[] (avatar, name, text, code blocks, reactions)
│   └── MessageInput (rich text, code snippets, @mentions)
└── MemberList (sidebar, online/offline status)
```

## State Architecture (Zustand Stores)

```
useAuthStore          — token, user, login(), logout(), refreshToken()
useRepoStore          — repository list, current repo
useEditorStore        — open files, active file, file tree
useCollabStore        — WebSocket connection, peers, cursors, operations
useNotificationStore  — unread count, notification list
useChatStore          — channels, messages, active channel
useSettingsStore      — theme, editor preferences, locale
```

## WebSocket Integration

- **Connection**: Single WebSocket connection per session (`/ws/`)
- **Authentication**: JWT token in query parameter
- **Message types**: heartbeat, operation, presence, notification, chat_message
- **Auto-reconnect**: Exponential backoff with jitter (1000ms base, 30s max)
- **Stores**: `useCollabStore` manages connection state, `useChatStore` manages messages

## CodeMirror 6 Integration

- **Extensions**:
  - `basicSetup` — line numbers, undo history, clipboard
  - `LanguageSupport` — TypeScript/JSX, Python, Go, Rust, JSON, Markdown
  - `CollabExtension` — custom extension for remote cursors/selections
  - `DiscussionGutter` — custom gutter with thread markers
  - `OneDarkTheme` — dark theme matching the prototype
- **Collaboration layer**:
  - CRDT operations sent via WebSocket
  - Remote cursor positions rendered as colored vertical bars + name labels
  - Remote selections rendered as translucent backgrounds

## UI / UX Conventions

- **Theme**: Dark mode only (GitHub-inspired dark palette)
  - `--bg-primary: #0d1117`
  - `--bg-secondary: #161b22`
  - `--accent: #1f6feb`
- **Typography**: Inter (UI), JetBrains Mono (code)
- **Design language**: Clean, minimal, JetBrains Space-inspired
  - Generous whitespace
  - Subtle borders, rounded corners
  - Gradient accents for brand moments
- **Ant Design customization**: Use `ConfigProvider` with `theme={{ algorithm: theme.darkAlgorithm, token: { colorPrimary: '#1f6feb', borderRadius: 8 } }}`
- **Modals**: Ant Design `Modal` for create/new actions
- **Notifications**: Ant Design `notification` API + `Badge` for navbar bell

## State Management Patterns

| State Type | Where | Example |
|------------|-------|---------|
| Server data | React Query / fetch | Repository list, commits, issues |
| UI state | Local `useState` | Tab selection, modal open |
| Global app state | Zustand | Auth, WebSocket, notifications |
| Form state | React Hook Form | Issue creation, PR form |
| URL state | React Router params | `:repoId`, `:issueNumber` |

## Search Feature

- Global search (Ctrl+K): Ant Design `AutoComplete` or custom modal
- Scoped search: per-repository code search via backend `ripgrep` endpoint
- Results: file paths with highlighted matches

## Responsive Behavior

- **Desktop-first**: Primary target is desktop browsers
- **Minimal responsive**: Sidebar collapses to icon-only on narrow screens
- **Chat page**: Adapts layout for mobile (bottom nav instead of sidebar)

import React from 'react'
import { createRoot } from 'react-dom/client'
import * as monaco from 'monaco-editor'
import { loader } from '@monaco-editor/react'
import App from './App'
import './styles/desktop.css'

self.MonacoEnvironment = {
  getWorker(_, label: string) {
    const esm = 'monaco-editor/esm/vs'
    const map: Record<string, string> = {
      json: `${esm}/language/json/json.worker?worker`,
      css: `${esm}/language/css/css.worker?worker`,
      html: `${esm}/language/html/html.worker?worker`,
      typescript: `${esm}/language/typescript/ts.worker?worker`,
      javascript: `${esm}/language/typescript/ts.worker?worker`,
      editorWorker: `${esm}/editor/editor.worker?worker`,
    }
    const mod = map[label] ?? map.editorWorker
    return new Worker(mod, { type: 'module' })
  },
}

loader.config({ monaco })

const container = document.getElementById('root')
const root = createRoot(container!)
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

// Package lsp 提供语言服务器进程管理与 LSP 帧（Content-Length）编解码。
// 网关仅做透明 JSON-RPC 桥：前端自定义 Monaco providers 驱动协议，本包负责进程生命周期与帧转换。
package lsp

import (
	"strings"
)

// Server 一个语言服务器注册项（spec §8.1）。
type Server struct {
	Language    string
	DisplayName string
	Command     []string
	InitOptions map[string]any
	Extensions  []string
	Env         []string
}

// Registry 语言 → 服务器。
type Registry map[string]Server

// DefaultRegistry 内置注册表：Python(pyright) + TS/JS(typescript-language-server)。
func DefaultRegistry() Registry {
	return Registry{
		"python": {
			Language:    "python",
			DisplayName: "Pyright",
			Command:     []string{"pyright-langserver", "--stdio"},
			InitOptions: map[string]any{},
			Extensions:  []string{".py"},
		},
		"typescript": {
			Language:    "typescript",
			DisplayName: "TypeScript Language Server",
			Command:     []string{"typescript-language-server", "--stdio"},
			InitOptions: map[string]any{},
			Extensions:  []string{".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"},
		},
	}
}

// ByLanguage 按语言查找服务器。
func (r Registry) ByLanguage(lang string) (Server, bool) {
	s, ok := r[strings.ToLower(lang)]
	return s, ok
}

// ByExtension 按文件扩展名推断语言并查找服务器。
func (r Registry) ByExtension(ext string) (Server, bool) {
	ext = strings.ToLower(strings.TrimPrefix(ext, "."))
	for _, s := range r {
		for _, e := range s.Extensions {
			if strings.TrimPrefix(e, ".") == ext {
				return s, true
			}
		}
	}
	return Server{}, false
}
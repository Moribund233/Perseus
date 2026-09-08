package lsp

// Manager 语言服务器管理：持有注册表，按语言启动会话。
// spec §8.1/8.2：注册表以常量内置，按首文件扩展名惰性启动。
type Manager struct {
	registry Registry
}

func NewManager() *Manager {
	return NewManagerWithRegistry(DefaultRegistry())
}

func NewManagerWithRegistry(r Registry) *Manager {
	return &Manager{registry: r}
}

// Registry 返回当前注册表（测试注入）。
func (m *Manager) Registry() Registry { return m.registry }

// Start 按语言启动一个会话（root 为工作区绝对路径）。
func (m *Manager) Start(root, lang string) (*Session, error) {
	srv, ok := m.registry.ByLanguage(lang)
	if !ok {
		return nil, ErrUnsupportedLanguage{Language: lang}
	}
	return NewSession(root, srv)
}

// DetectLanguage 按文件扩展名推断语言。
func (m *Manager) DetectLanguage(ext string) (string, bool) {
	if srv, ok := m.registry.ByExtension(ext); ok {
		return srv.Language, true
	}
	return "", false
}

// ErrUnsupportedLanguage 语言不在注册表中。
type ErrUnsupportedLanguage struct{ Language string }

func (e ErrUnsupportedLanguage) Error() string {
	return "lsp: unsupported language: " + e.Language
}
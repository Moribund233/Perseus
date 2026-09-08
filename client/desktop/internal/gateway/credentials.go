package gateway

import (
	"strings"

	"desktop/internal/git"
)

// matchServerCredential 按远程 URL 前缀匹配注册表服务器,
// 返回其密钥库 token 组成的 git 凭据; 未匹配返回零值凭据 (type="none" 语义由调用方保证)。
// 典型场景: clone/push/pull 指向已注册的 Perseus 服务器时, 免去用户手动输入凭据。
func (g *Gateway) matchServerCredential(remoteURL string) git.Credential {
	remoteURL = strings.TrimSpace(remoteURL)
	if remoteURL == "" {
		return git.Credential{}
	}
	items, err := g.servers.List()
	if err != nil {
		return git.Credential{}
	}
	for _, srv := range items {
		if srv.BaseURL == "" || !strings.HasPrefix(remoteURL, srv.BaseURL) {
			continue
		}
		tok, err := g.servers.Token(srv.ID)
		if err != nil || tok == "" {
			continue
		}
		return git.Credential{Type: "token", Token: tok}
	}
	return git.Credential{}
}

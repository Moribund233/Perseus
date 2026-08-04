package gateway

import (
	"encoding/json"
	"fmt"
	"net"
	"os"
	"testing"

	"desktop/internal/server"
	"desktop/internal/store"
)

// 冒烟验收：对真实部署的 Perseus 后端走网关代理端到端验证。
// 运行（必须已设 PERSEUS_SMOKE=1）：
//
//	PERSEUS_SMOKE=1 PERSEUS_SMOKE_BASE=http://192.168.31.176:8000 \
//	PERSEUS_SMOKE_USER=admin PERSEUS_SMOKE_PASS=... go test ./internal/gateway -run Smoke -v
func TestSmokeLiveBackend(t *testing.T) {
	if os.Getenv("PERSEUS_SMOKE") != "1" {
		t.Skip("smoke test disabled (set PERSEUS_SMOKE=1)")
	}
	base := env("PERSEUS_SMOKE_BASE", "http://192.168.31.176:8000")
	user := env("PERSEUS_SMOKE_USER", "admin")
	pass := os.Getenv("PERSEUS_SMOKE_PASS")

	st, _ := store.New("")
	t.Cleanup(func() { st.Close() })
	g := New(Config{
		Store:         st,
		Servers:       server.NewRegistry(st, &store.FakeKeychain{M: map[string]string{}}),
		AllowedOrigins: []string{"http://localhost:34115"},
	})

	// 1) 账密登录注册服务器 → 初始 health 应 online。
	rr := authedReq(t, g, "POST", "/api/local/servers", map[string]string{
		"name": "live", "base_url": base, "auth_method": "password",
		"username": user, "password": pass,
	})
	if rr.Code != 200 {
		t.Fatalf("register = %d body=%s", rr.Code, rr.Body.String())
	}
	var srv struct {
		ID string `json:"id"`
		Health string `json:"health"`
	}
	must(t, json.Unmarshal(rr.Body.Bytes(), &srv))
	if srv.ID == "" {
		t.Fatal("no server id")
	}
	t.Logf("registered server id=%s health=%s", srv.ID, srv.Health)
	if srv.Health != "online" {
		t.Fatalf("expected online, got %q", srv.Health)
	}
	id := srv.ID

	// 2) 公开仓库列表。
	rr = authedReq(t, g, "GET", "/api/local/proxy/"+id+"/api/v1/repositories/public", nil)
	if rr.Code != 200 {
		t.Fatalf("public repos = %d body=%s", rr.Code, rr.Body.String())
	}
	var repos []map[string]any
	must(t, json.Unmarshal(rr.Body.Bytes(), &repos))
	if len(repos) == 0 {
		t.Fatal("no public repos; check backend seed data")
	}
	t.Logf("public repos: %d", len(repos))
	first := repos[0]
	targetOwner := fmt.Sprint(first["path"])
	if targetOwner == "" {
		t.Fatal("repo has no path")
	}

	// 3) 仓库详情 + tree + readme + blob。
	rr = authedReq(t, g, "GET", "/api/local/proxy/"+id+"/api/v1/repositories/"+targetOwner, nil)
	if rr.Code != 200 {
		t.Fatalf("repo detail = %d body=%s", rr.Code, rr.Body.String())
	}
	var detail struct {
		ID            string `json:"id"`
		Status        struct{ Initialized bool `json:"initialized"` } `json:"status"`
	}
	must(t, json.Unmarshal(rr.Body.Bytes(), &detail))
	t.Logf("repo detail OK id=%s initialized=%v", detail.ID, detail.Status.Initialized)

	if detail.Status.Initialized {
		rr = authedReq(t, g, "GET", "/api/local/proxy/"+id+"/api/v1/repositories/"+detail.ID+"/tree", nil)
		if rr.Code != 200 {
			t.Fatalf("tree = %d body=%s", rr.Code, rr.Body.String())
		}
		var tree struct {
			Entries []struct {
				Name string `json:"name"`
				Type string `json:"type"`
			} `json:"entries"`
		}
		must(t, json.Unmarshal(rr.Body.Bytes(), &tree))
		t.Logf("tree entries: %d", len(tree.Entries))
	} else {
		// 元数据仓库无裸库：树接口返回后端自身 404，证明逐字节透传正确。
		rr = authedReq(t, g, "GET", "/api/local/proxy/"+id+"/api/v1/repositories/"+detail.ID+"/tree", nil)
		if rr.Code != 404 {
			t.Fatalf("uninitialized tree = %d body=%s (want backend 404 passthrough)", rr.Code, rr.Body.String())
		}
		t.Log("tree: uninitialized repo → backend 404 passthrough (OK)")
	}

	rr = authedReq(t, g, "GET", "/api/local/proxy/"+id+"/api/v1/repositories/"+detail.ID+"/branches", nil)
	if rr.Code != 200 {
		t.Fatalf("branches = %d body=%s", rr.Code, rr.Body.String())
	}
	t.Logf("branches OK")

	// 4) 离线语义：指向未监听端口。
	dead := pickDeadAddr(t)
	rr = authedReq(t, g, "POST", "/api/local/servers", map[string]string{
		"name": "dead", "base_url": "http://" + dead, "auth_method": "token", "token": "x",
	})
	// 不可达 → 注册也应仍入库但 health=offline。
	if rr.Code != 200 {
		t.Fatalf("register dead = %d body=%s", rr.Code, rr.Body.String())
	}
	var deadSrv struct{ ID string `json:"id"`; Health string `json:"health"` }
	must(t, json.Unmarshal(rr.Body.Bytes(), &deadSrv))
	t.Logf("dead server health=%s", deadSrv.Health)
	rr = authedReq(t, g, "GET", "/api/local/proxy/"+deadSrv.ID+"/api/v1/repositories/public", nil)
	if rr.Code != 503 {
		t.Fatalf("offline proxy = %d body=%s", rr.Code, rr.Body.String())
	}
	var off struct {
		Offline bool `json:"offline"`
		Cached  any  `json:"cached"`
	}
	must(t, json.Unmarshal(rr.Body.Bytes(), &off))
	if !off.Offline {
		t.Fatalf("expected offline:true, body=%s", rr.Body.String())
	}
	t.Logf("offline semantics OK (offline=%v cached=%v)", off.Offline, off.Cached)
}

func pickDeadAddr(t *testing.T) string {
	t.Helper()
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	addr := l.Addr().String()
	_ = l.Close()
	return addr
}

func env(k, fallback string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return fallback
}

func must(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatal(err)
	}
}
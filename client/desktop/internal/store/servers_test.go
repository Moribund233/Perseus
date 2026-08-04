package store

import "testing"

func TestServerCRUD(t *testing.T) {
	st, _ := New("")
	defer st.Close()

	srv, err := st.CreateServer(Server{Name: "dev", BaseURL: "http://127.0.0.1:8080", AuthMethod: "token", Health: "unknown"})
	if err != nil {
		t.Fatalf("CreateServer: %v", err)
	}
	if srv.ID == "" {
		t.Fatal("expected id")
	}

	got, err := st.GetServer(srv.ID)
	if err != nil || got.BaseURL != "http://127.0.0.1:8080" {
		t.Fatalf("GetServer = %+v, err %v", got, err)
	}

	if err := st.SetServerHealth(srv.ID, "online", "2026-08-04T00:00:00Z", "2026-08-04T00:00:00Z"); err != nil {
		t.Fatalf("SetServerHealth: %v", err)
	}
	got, _ = st.GetServer(srv.ID)
	if got.Health != "online" || got.LastChecked == "" {
		t.Fatalf("health not updated: %+v", got)
	}

	if err := st.UpdateServer(Server{ID: srv.ID, Name: "renamed", BaseURL: got.BaseURL, AuthMethod: got.AuthMethod}); err != nil {
		t.Fatalf("UpdateServer: %v", err)
	}
	got, _ = st.GetServer(srv.ID)
	if got.Name != "renamed" {
		t.Fatalf("name = %q", got.Name)
	}

	list, err := st.ListServers()
	if err != nil || len(list) != 1 {
		t.Fatalf("ListServers = %d items, err %v", len(list), err)
	}

	if err := st.DeleteServer(srv.ID); err != nil {
		t.Fatalf("DeleteServer: %v", err)
	}
	if _, err := st.GetServer(srv.ID); err == nil {
		t.Fatal("expected error after delete")
	}
}

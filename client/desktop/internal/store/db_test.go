package store

import (
	"strings"
	"testing"
)

func TestStoreWorkspaceCRUD(t *testing.T) {
	s, err := New("")
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	defer s.Close()

	ws, err := s.CreateWorkspace(Workspace{Name: "demo", Path: "C:/tmp/demo"})
	if err != nil {
		t.Fatalf("CreateWorkspace: %v", err)
	}
	if ws.ID == "" {
		t.Fatal("expected generated id")
	}
	if strings.Contains(ws.ID, "\x00") {
		t.Fatal("bad id")
	}

	got, err := s.GetWorkspace(ws.ID)
	if err != nil || got.Path != "C:/tmp/demo" {
		t.Fatalf("GetWorkspace = %+v, err %v", got, err)
	}

	list, err := s.ListWorkspaces()
	if err != nil || len(list) != 1 {
		t.Fatalf("ListWorkspaces = %+v, err %v", list, err)
	}

	if err := s.DeleteWorkspace(ws.ID); err != nil {
		t.Fatalf("DeleteWorkspace: %v", err)
	}
	if _, err := s.GetWorkspace(ws.ID); err == nil {
		t.Fatal("expected not found after delete")
	}
}

func TestStoreSettings(t *testing.T) {
	s, _ := New("")
	defer s.Close()
	if err := s.SetSetting("theme", "dark"); err != nil {
		t.Fatalf("SetSetting: %v", err)
	}
	v, err := s.GetSetting("theme")
	if err != nil || v != "dark" {
		t.Fatalf("GetSetting = %q, err %v", v, err)
	}
}

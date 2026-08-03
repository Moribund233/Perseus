package store

import "testing"

func TestFakeKeychain(t *testing.T) {
	k := &FakeKeychain{M: map[string]string{}}
	if err := k.Set("svc", "acct", "secret"); err != nil {
		t.Fatalf("Set: %v", err)
	}
	v, err := k.Get("svc", "acct")
	if err != nil || v != "secret" {
		t.Fatalf("Get = %q, err %v", v, err)
	}
	if err := k.Delete("svc", "acct"); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := k.Get("svc", "acct"); err == nil {
		t.Fatal("expected error after delete")
	}
}

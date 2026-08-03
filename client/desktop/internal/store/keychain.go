package store

import (
	"errors"

	"github.com/zalando/go-keyring"
)

type Keychain interface {
	Get(service, account string) (string, error)
	Set(service, account, secret string) error
	Delete(service, account string) error
}

// FakeKeychain 内存实现，仅用于测试。
type FakeKeychain struct{ M map[string]string }

func (f *FakeKeychain) Get(service, account string) (string, error) {
	v, ok := f.M[service+"\x00"+account]
	if !ok {
		return "", errors.New("not found")
	}
	return v, nil
}

func (f *FakeKeychain) Set(service, account, secret string) error {
	if f.M == nil {
		f.M = map[string]string{}
	}
	f.M[service+"\x00"+account] = secret
	return nil
}

func (f *FakeKeychain) Delete(service, account string) error {
	delete(f.M, service+"\x00"+account)
	return nil
}

// NewKeychain 返回生产实现（Windows Credential Manager）。
// 非 Windows 平台运行时返回 nil，调用方需自行处理（Phase 1 仅 Windows）。
func NewKeychain() Keychain {
	return &windowsKeychain{}
}

type windowsKeychain struct{}

func (w *windowsKeychain) Get(service, account string) (string, error) {
	return keyring.Get(service, account)
}

func (w *windowsKeychain) Set(service, account, secret string) error {
	return keyring.Set(service, account, secret)
}

func (w *windowsKeychain) Delete(service, account string) error {
	return keyring.Delete(service, account)
}

package store

import (
	"database/sql"
	"time"

	"github.com/google/uuid"
	_ "modernc.org/sqlite"
)

type Workspace struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	Path      string    `json:"path"`
	RemoteURL string    `json:"remote_url,omitempty"`
	ServerID  string    `json:"server_id,omitempty"`
	CreatedAt time.Time `json:"created_at"`
}

type Store struct {
	db *sql.DB
}

func New(path string) (*Store, error) {
	if path == "" {
		path = "file::memory:?cache=shared"
	}
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	if _, err := db.Exec(`
        CREATE TABLE IF NOT EXISTS workspaces (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            remote_url TEXT NOT NULL DEFAULT '',
            server_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    `); err != nil {
		db.Close()
		return nil, err
	}
	return &Store{db: db}, nil
}

func (s *Store) Close() error { return s.db.Close() }

func (s *Store) CreateWorkspace(ws Workspace) (Workspace, error) {
	ws.ID = uuid.NewString()
	ws.CreatedAt = time.Now().UTC()
	_, err := s.db.Exec(
		`INSERT INTO workspaces (id, name, path, remote_url, server_id, created_at) VALUES (?,?,?,?,?,?)`,
		ws.ID, ws.Name, ws.Path, ws.RemoteURL, ws.ServerID,
		ws.CreatedAt.Format(time.RFC3339),
	)
	return ws, err
}

func (s *Store) ListWorkspaces() ([]Workspace, error) {
	rows, err := s.db.Query(`SELECT id, name, path, remote_url, server_id, created_at FROM workspaces ORDER BY created_at DESC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Workspace
	for rows.Next() {
		var ws Workspace
		var ts string
		if err := rows.Scan(&ws.ID, &ws.Name, &ws.Path, &ws.RemoteURL, &ws.ServerID, &ts); err != nil {
			return nil, err
		}
		if ws.CreatedAt, err = time.Parse(time.RFC3339, ts); err != nil {
			return nil, err
		}
		out = append(out, ws)
	}
	return out, rows.Err()
}

func (s *Store) GetWorkspace(id string) (Workspace, error) {
	var ws Workspace
	var ts string
	err := s.db.QueryRow(
		`SELECT id, name, path, remote_url, server_id, created_at FROM workspaces WHERE id = ?`, id,
	).Scan(&ws.ID, &ws.Name, &ws.Path, &ws.RemoteURL, &ws.ServerID, &ts)
	if err != nil {
		return Workspace{}, err
	}
	ws.CreatedAt, err = time.Parse(time.RFC3339, ts)
	return ws, err
}

func (s *Store) DeleteWorkspace(id string) error {
	_, err := s.db.Exec(`DELETE FROM workspaces WHERE id = ?`, id)
	return err
}

func (s *Store) SetSetting(key, value string) error {
	_, err := s.db.Exec(`INSERT INTO settings (key, value) VALUES (?,?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value`, key, value)
	return err
}

func (s *Store) GetSetting(key string) (string, error) {
	var v string
	err := s.db.QueryRow(`SELECT value FROM settings WHERE key = ?`, key).Scan(&v)
	return v, err
}

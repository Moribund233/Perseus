package store

import (
	"time"

	"github.com/google/uuid"
)

// Server 服务器注册表实体，仅存非敏感元数据。
// 敏感数据（token/密码）存放于系统密钥库，key 为 server:<id>:token。
type Server struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	BaseURL     string    `json:"base_url"`
	AuthMethod  string    `json:"auth_method"` // "password" | "token"
	Username    string    `json:"username,omitempty"`
	Health      string    `json:"health"` // "online" | "offline" | "unknown"
	LastChecked string    `json:"last_checked,omitempty"`
	LastSuccess string    `json:"last_success,omitempty"`
	CreatedAt   time.Time `json:"created_at"`
}

func (s *Store) CreateServer(srv Server) (Server, error) {
	srv.ID = uuid.NewString()
	srv.CreatedAt = time.Now().UTC()
	_, err := s.db.Exec(
		`INSERT INTO servers (id, name, base_url, auth_method, username, health, last_checked, last_success, created_at)
         VALUES (?,?,?,?,?,?,?,?,?)`,
		srv.ID, srv.Name, srv.BaseURL, srv.AuthMethod, srv.Username,
		srv.Health, srv.LastChecked, srv.LastSuccess, srv.CreatedAt.Format(time.RFC3339),
	)
	return srv, err
}

func (s *Store) ListServers() ([]Server, error) {
	rows, err := s.db.Query(`SELECT id, name, base_url, auth_method, username, health, last_checked, last_success, created_at FROM servers ORDER BY created_at ASC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Server
	for rows.Next() {
		var srv Server
		if err := scanServer(rows, &srv); err != nil {
			return nil, err
		}
		out = append(out, srv)
	}
	return out, rows.Err()
}

func (s *Store) GetServer(id string) (Server, error) {
	row := s.db.QueryRow(
		`SELECT id, name, base_url, auth_method, username, health, last_checked, last_success, created_at FROM servers WHERE id = ?`, id)
	var srv Server
	if err := scanServer(row, &srv); err != nil {
		return Server{}, err
	}
	return srv, nil
}

func (s *Store) UpdateServer(srv Server) error {
	_, err := s.db.Exec(
		`UPDATE servers SET name=?, base_url=?, auth_method=?, username=?, health=?, last_checked=?, last_success=? WHERE id=?`,
		srv.Name, srv.BaseURL, srv.AuthMethod, srv.Username,
		srv.Health, srv.LastChecked, srv.LastSuccess, srv.ID,
	)
	return err
}

func (s *Store) SetServerHealth(id, health, checked, success string) error {
	_, err := s.db.Exec(
		`UPDATE servers SET health=?, last_checked=?, last_success=? WHERE id=?`,
		health, checked, success, id,
	)
	return err
}

func (s *Store) DeleteServer(id string) error {
	_, err := s.db.Exec(`DELETE FROM servers WHERE id = ?`, id)
	return err
}

type rowScanner interface {
	Scan(dest ...any) error
}

func scanServer(r rowScanner, srv *Server) error {
	var ts string
	if err := r.Scan(&srv.ID, &srv.Name, &srv.BaseURL, &srv.AuthMethod, &srv.Username,
		&srv.Health, &srv.LastChecked, &srv.LastSuccess, &ts); err != nil {
		return err
	}
	createdAt, err := time.Parse(time.RFC3339, ts)
	if err != nil {
		return err
	}
	srv.CreatedAt = createdAt
	return nil
}

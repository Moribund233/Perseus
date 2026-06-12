export interface ApiError {
  detail: string
  error_code?: string
  request_id?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface RefreshTokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserCreateRequest {
  username: string
  email: string
  password: string
  full_name?: string
}

export interface UserUpdateRequest {
  username?: string
  email?: string
  full_name?: string
}

export interface User {
  id: number
  username: string
  email: string
  full_name?: string
  is_active: boolean
  is_admin: boolean
  created_at: string
  updated_at?: string
}

export interface Repository {
  id: number
  name: string
  full_name: string
  description?: string
  owner_id: number
  owner?: User
  is_public: boolean
  default_branch: string
  language?: string
  stars_count: number
  forks_count: number
  created_at: string
  updated_at?: string
}

export interface RepositoryCreateRequest {
  name: string
  description?: string
  is_public?: boolean
  default_branch?: string
}

export interface Branch {
  id: number
  repository_id: number
  name: string
  commit_hash?: string
  is_default: boolean
  is_protected: boolean
  created_at: string
}

export interface Commit {
  id: number
  repository_id: number
  commit_hash: string
  message: string
  author_name: string
  author_email: string
  authored_at: string
  branch_name?: string
}

export interface PullRequest {
  id: number
  repository_id: number
  number: number
  title: string
  description?: string
  source_branch: string
  target_branch: string
  status: string
  author?: User
  created_at: string
  updated_at?: string
}

export interface Issue {
  id: number
  repository_id: number
  number: number
  title: string
  description?: string
  status: string
  priority?: string
  author?: User
  assignee?: User
  labels?: IssueLabel[]
  created_at: string
  updated_at?: string
}

export interface IssueCreateRequest {
  title: string
  description?: string
  priority?: string
  assignee_id?: number
  label_ids?: number[]
}

export interface IssueLabel {
  id: number
  name: string
  color: string
  description?: string
}

export interface SSHKey {
  id: number
  name: string
  public_key: string
  created_at: string
}

export interface AddSSHKeyRequest {
  name: string
  public_key: string
}

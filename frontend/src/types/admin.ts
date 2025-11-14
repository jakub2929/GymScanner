export interface AdminUser {
  id: number;
  name: string;
  email: string;
  credits: number;
  is_admin: boolean;
  created_at?: string | null;
}

export interface AdminToken {
  id: number;
  token: string;
  user_id: number | null;
  user_name: string | null;
  user_email: string | null;
  expires_at?: string | null;
  created_at?: string | null;
  used_at?: string | null;
  is_active: boolean;
  scan_count: number;
  qr_code_url: string;
}

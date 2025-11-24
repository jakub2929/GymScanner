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

export interface AdminScanLog {
  id: number;
  user_id: number | null;
  user_name: string | null;
  reason?: string | null;
  status: string;
  allowed?: boolean | null;
  created_at?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface AdminMembershipPackage {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  price_czk: number;
  duration_days: number;
  daily_entry_limit?: number | null;
  session_limit?: number | null;
  package_type: string;
  is_active: boolean;
  metadata?: Record<string, unknown> | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AdminUserMembership {
  id: number;
  user_id: number;
  package_id?: number | null;
  package_name: string | null;
  membership_type: string;
  status: string;
  price_czk?: number | null;
  valid_from?: string | null;
  valid_to?: string | null;
  daily_limit_enabled?: boolean;
  daily_limit?: number | null;
  daily_usage_count?: number | null;
  sessions_total?: number | null;
  sessions_used?: number | null;
  auto_renew: boolean;
  notes?: string | null;
  metadata?: Record<string, unknown> | null;
  last_usage_at?: string | null;
  created_at?: string | null;
}

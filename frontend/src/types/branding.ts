export interface BrandingConfig {
  brandName: string;
  consoleName: string;
  tagline?: string | null;
  supportEmail?: string | null;
  primaryColor: string;
  footerText?: string | null;
  logoUrl?: string | null;
  reservationsEnabled: boolean;
}

export const defaultBranding: BrandingConfig = {
  brandName: 'Gym Access',
  consoleName: 'Control Console',
  tagline: 'Smart access management',
  supportEmail: 'support@example.com',
  primaryColor: '#0EA5E9',
  footerText: '© 2025 GymScanner',
  logoUrl: '/logo-default.svg',
  reservationsEnabled: false,
};

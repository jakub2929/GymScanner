import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from '@/components/providers';
import type { BrandingConfig } from '@/types/branding';
import { defaultBranding } from '@/types/branding';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchBranding(): Promise<BrandingConfig> {
  try {
    const response = await fetch(`${API_URL}/api/branding`, {
      next: { revalidate: 60 },
    });

    if (!response.ok) {
      throw new Error(`Branding API failed (${response.status})`);
    }

    const data = await response.json();
    return {
      brandName: data.brand_name ?? defaultBranding.brandName,
      consoleName: data.console_name ?? defaultBranding.consoleName,
      tagline: data.tagline ?? defaultBranding.tagline,
      supportEmail: data.support_email ?? defaultBranding.supportEmail,
      primaryColor: data.primary_color ?? defaultBranding.primaryColor,
      footerText: data.footer_text ?? defaultBranding.footerText,
      logoUrl: data.logo_url ?? defaultBranding.logoUrl,
    };
  } catch (error) {
    console.error('Failed to load branding', error);
    return defaultBranding;
  }
}

export async function generateMetadata(): Promise<Metadata> {
  const branding = await fetchBranding();
  return {
    title: `${branding.brandName} Console`,
    description: branding.tagline ?? defaultBranding.tagline ?? 'Access control',
  };
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const branding = await fetchBranding();
  return (
    <html lang="cs" style={{ ['--brand-primary' as string]: branding.primaryColor }}>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <Providers branding={branding}>{children}</Providers>
      </body>
    </html>
  );
}

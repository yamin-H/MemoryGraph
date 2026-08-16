import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { AppShell } from '@/components/AppShell';
import './globals.css';

const inter = Inter({
  variable: '--font-sans',
  subsets: ['latin'],
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  variable: '--font-mono',
  subsets: ['latin'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'MemoryGraph — Graph-native Agent Memory on HydraDB',
  description: 'Temporal knowledge graph memory system for long-term AI agent memory and multi-session reasoning with confidence-aware abstention.',
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable} dark`} suppressHydrationWarning>
      <body className="font-sans antialiased bg-[#080b11] text-slate-100 min-h-screen" suppressHydrationWarning>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}

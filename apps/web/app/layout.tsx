import type { Metadata } from 'next';
import { Inter, JetBrains_Mono, Plus_Jakarta_Sans } from 'next/font/google';
import { AppShell } from '@/components/AppShell';
import { ThemeProvider } from '@/components/ThemeProvider';
import './globals.css';

const inter = Inter({
  variable: '--font-sans',
  subsets: ['latin'],
  display: 'swap',
});

const plusJakarta = Plus_Jakarta_Sans({
  variable: '--font-heading',
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
  description: 'Temporal knowledge graph memory layer for AI agents with recursive SUPERSEDES edges, multi-hop reasoning, and calibrated honest abstention.',
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
    <html lang="en" className={`${inter.variable} ${plusJakarta.variable} ${jetbrainsMono.variable} dark`} suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                const theme = localStorage.getItem('memorygraph_theme');
                if (theme === 'light' || (!theme && window.matchMedia('(prefers-color-scheme: light)').matches)) {
                  document.documentElement.classList.remove('dark');
                  document.documentElement.classList.add('light');
                  document.documentElement.style.colorScheme = 'light';
                } else {
                  document.documentElement.classList.add('dark');
                  document.documentElement.classList.remove('light');
                  document.documentElement.style.colorScheme = 'dark';
                }
              } catch (e) {}
            `,
          }}
        />
      </head>
      <body className="font-sans antialiased text-slate-900 dark:text-slate-100 min-h-screen relative transition-colors duration-200" suppressHydrationWarning>
        {/* Layered ambient background glow */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
          <div className="absolute -top-[20%] left-1/2 -translate-x-1/2 w-[850px] h-[480px] bg-gradient-to-b from-amber-400/[0.14] dark:from-amber-500/[0.08] via-sky-400/[0.08] dark:via-blue-500/[0.04] to-transparent rounded-full blur-[130px]" />
          <div className="absolute top-[35%] -left-[10%] w-[600px] h-[600px] bg-sky-400/[0.07] dark:bg-blue-500/[0.03] rounded-full blur-[140px]" />
          <div className="absolute bottom-[5%] -right-[10%] w-[600px] h-[600px] bg-amber-400/[0.08] dark:bg-amber-500/[0.04] rounded-full blur-[140px]" />
        </div>

        <ThemeProvider>
          <div className="relative z-10 h-screen overflow-hidden">
            <AppShell>{children}</AppShell>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}

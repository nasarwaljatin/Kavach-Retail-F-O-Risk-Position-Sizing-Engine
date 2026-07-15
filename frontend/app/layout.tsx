import './globals.css';
import Sidebar from '@/components/Sidebar';
import React from 'react';

export const metadata = {
  title: 'Kavach — Retail F&O Risk & Sizing Engine',
  description: 'Real-time guardrail engine for personal F&O trading.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div style={layoutStyles.container}>
          <Sidebar />
          <main style={layoutStyles.mainContent}>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}

const layoutStyles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    minHeight: '100vh',
    backgroundColor: '#0a0f1d'
  },
  mainContent: {
    marginLeft: '260px',
    flexGrow: 1,
    padding: '40px',
    minHeight: '100vh',
    overflowY: 'auto'
  }
};

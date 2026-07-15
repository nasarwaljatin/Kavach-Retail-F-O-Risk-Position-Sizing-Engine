'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Sidebar() {
  const pathname = usePathname();
  const [marketStatus, setMarketStatus] = useState<'OPEN' | 'CLOSED'>('CLOSED');
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const updateTimeAndStatus = () => {
      // Indian Standard Time (IST) is UTC+5.5
      const now = new Date();
      const utc = now.getTime() + now.getTimezoneOffset() * 60000;
      const istTime = new Date(utc + 3600000 * 5.5);
      
      const day = istTime.getDay(); // Sunday = 0, Saturday = 6
      const hour = istTime.getHours();
      const min = istTime.getMinutes();
      
      const currentMinutes = hour * 60 + min;
      const startMinutes = 9 * 60 + 15; // 9:15 AM
      const endMinutes = 15 * 60 + 30; // 3:30 PM
      
      const isWeekday = day >= 1 && day <= 5;
      const isMarketTime = currentMinutes >= startMinutes && currentMinutes <= endMinutes;

      if (isWeekday && isMarketTime) {
        setMarketStatus('OPEN');
      } else {
        setMarketStatus('CLOSED');
      }

      setTimeStr(
        istTime.toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: true,
          timeZone: 'UTC'
        }) + ' IST'
      );
    };

    updateTimeAndStatus();
    const interval = setInterval(updateTimeAndStatus, 1000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: '🛡️' },
    { name: 'Settings', path: '/settings', icon: '⚙️' }
  ];

  return (
    <aside style={styles.sidebar}>
      <div style={styles.brand}>
        <span style={styles.logo}>🛡️</span>
        <h1 style={styles.title}>KAVACH</h1>
      </div>

      <nav style={styles.nav}>
        {navItems.map((item) => {
          const isActive = pathname === item.path;
          return (
            <Link key={item.path} href={item.path} style={{
              ...styles.navLink,
              ...(isActive ? styles.navLinkActive : {})
            }}>
              <span style={styles.navIcon}>{item.icon}</span>
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div style={styles.statusBox}>
        <div style={styles.statusRow}>
          <span style={styles.statusLabel}>Market Clock:</span>
        </div>
        <div style={styles.timeValue}>{timeStr}</div>
        <div style={styles.statusRow}>
          <span style={styles.statusLabel}>Status:</span>
          <span style={{
            ...styles.statusIndicator,
            ...(marketStatus === 'OPEN' ? styles.statusOpen : styles.statusClosed)
          }}>
            {marketStatus}
          </span>
        </div>
      </div>

      <div style={styles.footer}>
        <div style={styles.paperBadge}>
          <span style={styles.badgeDot}></span>
          PAPER MODE ACTIVE
        </div>
      </div>
    </aside>
  );
}

const styles: Record<string, React.CSSProperties> = {
  sidebar: {
    width: '260px',
    height: '100vh',
    position: 'fixed',
    top: 0,
    left: 0,
    backgroundColor: '#0c1224',
    borderRight: '1px solid rgba(255, 255, 255, 0.05)',
    display: 'flex',
    flexDirection: 'column',
    padding: '24px 16px',
    zIndex: 100
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '40px',
    paddingLeft: '8px'
  },
  logo: {
    fontSize: '1.8rem'
  },
  title: {
    fontSize: '1.3rem',
    fontWeight: '800',
    letterSpacing: '2px',
    background: 'linear-gradient(135deg, #fff 0%, #3b82f6 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent'
  },
  nav: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    flexGrow: 1
  },
  navLink: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 16px',
    borderRadius: '10px',
    color: '#94a3b8',
    fontWeight: '500',
    fontSize: '0.95rem',
    transition: 'all 0.15s ease'
  },
  navLinkActive: {
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
    color: '#3b82f6',
    border: '1px solid rgba(59, 130, 246, 0.2)'
  },
  navIcon: {
    fontSize: '1.1rem'
  },
  statusBox: {
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    border: '1px solid rgba(255, 255, 255, 0.04)',
    borderRadius: '12px',
    padding: '16px',
    marginBottom: '20px'
  },
  statusRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '4px',
    fontSize: '0.8rem'
  },
  statusLabel: {
    color: '#64748b',
    fontWeight: '500'
  },
  timeValue: {
    fontSize: '0.9rem',
    fontWeight: '700',
    color: '#f8fafc',
    marginBottom: '8px',
    fontFamily: 'monospace'
  },
  statusIndicator: {
    fontWeight: '700',
    fontSize: '0.75rem',
    padding: '2px 6px',
    borderRadius: '4px'
  },
  statusOpen: {
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    color: '#10b981'
  },
  statusClosed: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    color: '#ef4444'
  },
  footer: {
    borderTop: '1px solid rgba(255,255,255,0.05)',
    paddingTop: '16px',
    display: 'flex',
    justifyContent: 'center'
  },
  paperBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '8px',
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
    border: '1px solid rgba(245, 158, 11, 0.2)',
    color: '#f59e0b',
    fontSize: '0.75rem',
    fontWeight: '700',
    padding: '6px 12px',
    borderRadius: '30px',
    letterSpacing: '0.5px'
  },
  badgeDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#f59e0b',
    boxShadow: '0 0 8px #f59e0b'
  }
};

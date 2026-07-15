'use client';

import React from 'react';
import { RiskEvent } from '@/lib/types';

interface RiskEventLogProps {
  events: RiskEvent[];
}

export default function RiskEventLog({ events }: RiskEventLogProps) {
  const getActionBadgeClass = (action: string) => {
    switch (action) {
      case 'squared_off':
        return 'badge-danger';
      case 'blocked':
        return 'badge-warning';
      default:
        return 'badge-safe';
    }
  };

  const getFormatDetails = (detailsStr: string) => {
    try {
      const details = JSON.parse(detailsStr);
      return `Breakers: [${details.triggered_breakers?.join(', ')}] | P&L: ₹${details.account_state?.day_pnl?.toLocaleString('en-IN')}`;
    } catch {
      return detailsStr;
    }
  };

  return (
    <div className="glass-card" style={styles.card}>
      <h3 style={styles.title}>Recent Risk Events & Triggers</h3>
      
      <div style={styles.logContainer}>
        {events.length === 0 ? (
          <div style={styles.emptyState}>
            <span>🛡️</span>
            <p>No risk violations logged today.</p>
          </div>
        ) : (
          <div style={styles.list}>
            {events.map((event) => {
              const eventDate = new Date(event.ts);
              const formattedTime = eventDate.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
              });
              
              return (
                <div key={event.id} style={styles.item}>
                  <div style={styles.itemHeader}>
                    <span style={styles.time}>{formattedTime}</span>
                    <span style={styles.breakerType}>⚠️ {event.breakerType}</span>
                    <span className={`badge ${getActionBadgeClass(event.actionTaken)}`} style={styles.actionBadge}>
                      {event.actionTaken.replace('_', ' ')}
                    </span>
                  </div>
                  <div style={styles.itemDetails}>
                    {getFormatDetails(event.details)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    width: '100%',
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    maxHeight: '350px'
  },
  title: {
    color: '#94a3b8',
    fontWeight: '600',
    fontSize: '0.85rem',
    textTransform: 'uppercase',
    letterSpacing: '1px',
    marginBottom: '20px'
  },
  logContainer: {
    overflowY: 'auto',
    flexGrow: 1
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px 0',
    color: '#64748b',
    gap: '8px',
    fontSize: '0.9rem'
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px'
  },
  item: {
    padding: '12px 16px',
    backgroundColor: 'rgba(255, 255, 255, 0.01)',
    border: '1px solid rgba(255, 255, 255, 0.03)',
    borderRadius: '8px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
  },
  itemHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px'
  },
  time: {
    fontSize: '0.85rem',
    color: '#64748b',
    fontWeight: '600',
    fontFamily: 'monospace'
  },
  breakerType: {
    fontSize: '0.85rem',
    fontWeight: '700',
    color: '#f8fafc',
    flexGrow: 1
  },
  actionBadge: {
    fontSize: '0.65rem',
    padding: '2px 6px',
    borderRadius: '4px'
  },
  itemDetails: {
    fontSize: '0.8rem',
    color: '#94a3b8',
    fontFamily: 'monospace',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis'
  }
};

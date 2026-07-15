'use client';

import React from 'react';

interface PnLCardProps {
  dayPnl: number;
  dayPnlPct: number;
  capitalBase: number;
  maxDailyLossPct: number;
}

export default function PnLCard({ dayPnl, dayPnlPct, capitalBase, maxDailyLossPct }: PnLCardProps) {
  const isLoss = dayPnl < 0;
  const formattedPnL = (dayPnl >= 0 ? '+' : '') + dayPnl.toLocaleString('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2
  });

  // Calculate percentage of daily loss budget consumed
  const dailyLossLimitVal = capitalBase * (maxDailyLossPct / 100);
  const lossBudgetConsumedPct = isLoss 
    ? Math.min((Math.abs(dayPnl) / dailyLossLimitVal) * 100, 100) 
    : 0;

  let progressColor = '#10b981'; // Green for profit
  if (isLoss) {
    if (lossBudgetConsumedPct < 50) {
      progressColor = '#f59e0b'; // Amber
    } else {
      progressColor = '#ef4444'; // Red
    }
  }

  return (
    <div className="glass-card" style={styles.card}>
      <div style={styles.header}>
        <span style={styles.title}>Daily Performance</span>
        <span className={`badge ${isLoss ? 'badge-danger' : 'badge-safe'}`}>
          {dayPnlPct >= 0 ? 'PROFIT' : 'LOSS'}
        </span>
      </div>

      <div style={{
        ...styles.pnlValue,
        color: isLoss ? '#ef4444' : '#10b981'
      }}>
        {formattedPnL}
      </div>

      <div style={styles.pctChange}>
        {dayPnlPct >= 0 ? '▲' : '▼'} {Math.abs(dayPnlPct).toFixed(2)}% of capital
      </div>

      <div style={styles.progressContainer}>
        <div style={styles.progressHeader}>
          <span style={styles.progressLabel}>
            {isLoss ? 'Daily Loss Limit Consumed' : 'Loss Limit Cushion'}
          </span>
          <span style={{
            ...styles.progressValue,
            color: progressColor
          }}>
            {isLoss ? `${lossBudgetConsumedPct.toFixed(1)}%` : '100.0%'}
          </span>
        </div>
        <div style={styles.progressBarBg}>
          <div style={{
            ...styles.progressBarFill,
            width: isLoss ? `${lossBudgetConsumedPct}%` : '100%',
            backgroundColor: progressColor,
            boxShadow: `0 0 10px ${progressColor}80`
          }}></div>
        </div>
        <div style={styles.progressFooter}>
          <span>Limit: {maxDailyLossPct}% (₹{dailyLossLimitVal.toLocaleString('en-IN')})</span>
          <span>Capital: ₹{capitalBase.toLocaleString('en-IN')}</span>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    flex: 1,
    minWidth: '280px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px'
  },
  title: {
    color: '#94a3b8',
    fontWeight: '600',
    fontSize: '0.85rem',
    textTransform: 'uppercase',
    letterSpacing: '1px'
  },
  pnlValue: {
    fontSize: '2.2rem',
    fontWeight: '800',
    marginBottom: '4px',
    letterSpacing: '-1px'
  },
  pctChange: {
    fontSize: '0.85rem',
    fontWeight: '600',
    color: '#64748b',
    marginBottom: '24px'
  },
  progressContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
  },
  progressHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.75rem',
    fontWeight: '600'
  },
  progressLabel: {
    color: '#94a3b8'
  },
  progressValue: {
    fontFamily: 'monospace'
  },
  progressBarBg: {
    width: '100%',
    height: '6px',
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: '3px',
    overflow: 'hidden'
  },
  progressBarFill: {
    height: '100%',
    borderRadius: '3px',
    transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
  },
  progressFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.7rem',
    color: '#64748b',
    fontWeight: '500'
  }
};

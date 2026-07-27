'use client';

import React from 'react';

interface RiskMeterProps {
  marginUtilisationPct: number;
  activeBreakers: string[];
  riskLevel: 'safe' | 'warning' | 'danger';
}

export default function RiskMeter({ marginUtilisationPct = 0, activeBreakers = [], riskLevel = 'safe' }: RiskMeterProps) {
  const safeMargin = marginUtilisationPct ?? 0;
  const safeBreakers = activeBreakers ?? [];
  const safeLevel = riskLevel || 'safe';

  // SVGs for circle gauges
  const radius = 60;
  const strokeWidth = 10;
  const circumference = 2 * Math.PI * radius;
  
  // Cap margin utilisation at 100 for gauge sizing
  const capUtilisation = Math.min(Math.max(safeMargin, 0), 100);
  const strokeDashoffset = circumference - (capUtilisation / 100) * circumference;

  let meterColor = '#10b981'; // safe green
  let glowColor = 'rgba(16, 185, 129, 0.2)';
  
  if (safeLevel === 'warning') {
    meterColor = '#f59e0b'; // amber
    glowColor = 'rgba(245, 158, 11, 0.2)';
  } else if (safeLevel === 'danger') {
    meterColor = '#ef4444'; // red
    glowColor = 'rgba(239, 68, 68, 0.3)';
  }

  return (
    <div className={`glass-card ${riskLevel === 'danger' ? 'pulse-danger' : riskLevel === 'warning' ? 'pulse-warning' : ''}`} style={styles.card}>
      <div style={styles.header}>
        <span style={styles.title}>Account Risk Level</span>
        <span className={`badge ${
          riskLevel === 'danger' ? 'badge-danger' : riskLevel === 'warning' ? 'badge-warning' : 'badge-safe'
        }`}>
          {riskLevel}
        </span>
      </div>

      <div style={styles.meterContainer}>
        <svg width="150" height="150" style={styles.svg}>
          {/* Background track */}
          <circle
            cx="75"
            cy="75"
            r={radius}
            fill="transparent"
            stroke="rgba(255,255,255,0.03)"
            strokeWidth={strokeWidth}
          />
          {/* Progress circle */}
          <circle
            cx="75"
            cy="75"
            r={radius}
            fill="transparent"
            stroke={meterColor}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            transform="rotate(-90 75 75)"
            style={{
              transition: 'stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
              filter: `drop-shadow(0px 0px 6px ${meterColor}cc)`
            }}
          />
          {/* Center text */}
          <text
            x="75"
            y="70"
            textAnchor="middle"
            fill="#f8fafc"
            fontSize="1.6rem"
            fontWeight="800"
            dy=".3em"
          >
            {safeMargin.toFixed(0)}%
          </text>
          <text
            x="75"
            y="98"
            textAnchor="middle"
            fill="#64748b"
            fontSize="0.65rem"
            fontWeight="600"
            letterSpacing="0.5px"
          >
            MARGIN USED
          </text>
        </svg>
      </div>

      <div style={styles.breakersBox}>
        <div style={styles.breakersLabel}>Active Risk Triggers:</div>
        {safeBreakers.length === 0 ? (
          <div style={styles.noBreakers}>✓ System standing by. No limits breached.</div>
        ) : (
          <div style={styles.breakersList}>
            {safeBreakers.map((breaker) => (
              <span key={breaker} className="badge badge-danger" style={styles.breakerBadge}>
                ⚠️ {breaker}
              </span>
            ))}
          </div>
        )}
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
    marginBottom: '10px'
  },
  title: {
    color: '#94a3b8',
    fontWeight: '600',
    fontSize: '0.85rem',
    textTransform: 'uppercase',
    letterSpacing: '1px'
  },
  meterContainer: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '16px 0'
  },
  svg: {
    overflow: 'visible'
  },
  breakersBox: {
    marginTop: '10px'
  },
  breakersLabel: {
    fontSize: '0.75rem',
    fontWeight: '600',
    color: '#64748b',
    marginBottom: '8px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  noBreakers: {
    fontSize: '0.8rem',
    color: '#10b981',
    fontWeight: '600'
  },
  breakersList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px'
  },
  breakerBadge: {
    fontSize: '0.7rem',
    padding: '4px 8px',
    borderRadius: '4px',
    fontWeight: '700'
  }
};

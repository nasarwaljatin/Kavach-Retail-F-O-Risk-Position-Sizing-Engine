'use client';

import React from 'react';
import { Position } from '@/lib/types';

interface PositionTableProps {
  positions: Position[];
}

export default function PositionTable({ positions }: PositionTableProps) {
  return (
    <div className="glass-card" style={styles.card}>
      <h3 style={styles.title}>Open F&O Positions</h3>
      
      <div style={styles.tableWrapper}>
        {positions.length === 0 ? (
          <div style={styles.emptyState}>
            <span style={styles.emptyIcon}>📦</span>
            <p>No active positions open.</p>
          </div>
        ) : (
          <table className="custom-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Exchange</th>
                <th>Qty</th>
                <th>Avg Price</th>
                <th>LTP</th>
                <th>Exposure</th>
                <th>Concentration %</th>
                <th style={{ textAlign: 'right' }}>P&L</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos) => {
                const isLoss = pos.pnl < 0;
                const isHighConcentration = pos.concentrationPct >= 20.0;
                
                return (
                  <tr key={pos.symbol}>
                    <td style={styles.symbolCell}>
                      <span style={styles.symbolName}>{pos.symbol}</span>
                      <span className={`badge ${
                        pos.instrumentType === 'EQ' ? 'badge-safe' : 'badge-danger'
                      }`} style={styles.instBadge}>
                        {pos.instrumentType}
                      </span>
                    </td>
                    <td>{pos.exchange}</td>
                    <td style={{ fontWeight: '600' }}>{pos.qty}</td>
                    <td>₹{pos.avgPrice.toFixed(2)}</td>
                    <td>₹{pos.ltp.toFixed(2)}</td>
                    <td>₹{pos.exposure.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                    <td>
                      <div style={styles.concentrationCol}>
                        <span style={{ 
                          fontWeight: '600',
                          color: isHighConcentration ? '#ef4444' : '#f8fafc'
                        }}>
                          {pos.concentrationPct.toFixed(1)}%
                        </span>
                        <div style={styles.miniBarBg}>
                          <div style={{
                            ...styles.miniBarFill,
                            width: `${Math.min(pos.concentrationPct, 100)}%`,
                            backgroundColor: isHighConcentration ? '#ef4444' : '#3b82f6'
                          }} />
                        </div>
                      </div>
                    </td>
                    <td style={{
                      ...styles.pnlCell,
                      color: isLoss ? '#ef4444' : '#10b981'
                    }}>
                      {pos.pnl >= 0 ? '+' : ''}₹{pos.pnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    width: '100%',
    padding: '24px',
    overflow: 'hidden'
  },
  title: {
    color: '#94a3b8',
    fontWeight: '600',
    fontSize: '0.85rem',
    textTransform: 'uppercase',
    letterSpacing: '1px',
    marginBottom: '20px'
  },
  tableWrapper: {
    width: '100%',
    overflowX: 'auto'
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '48px 0',
    color: '#64748b',
    gap: '12px'
  },
  emptyIcon: {
    fontSize: '2.5rem'
  },
  symbolCell: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  symbolName: {
    fontWeight: '700',
    color: '#f8fafc'
  },
  instBadge: {
    fontSize: '0.65rem',
    padding: '2px 4px',
    borderRadius: '3px'
  },
  concentrationCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    width: '100px'
  },
  miniBarBg: {
    width: '100%',
    height: '4px',
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: '2px',
    overflow: 'hidden'
  },
  miniBarFill: {
    height: '100%',
    borderRadius: '2px'
  },
  pnlCell: {
    textAlign: 'right',
    fontWeight: '700',
    fontFamily: 'monospace',
    fontSize: '0.95rem'
  }
};

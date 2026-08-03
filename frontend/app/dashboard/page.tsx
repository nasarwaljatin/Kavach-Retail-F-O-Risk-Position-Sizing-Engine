'use client';

import React, { useEffect, useState, useCallback } from 'react';
import PnLCard from '@/components/PnLCard';
import RiskMeter from '@/components/RiskMeter';
import KillSwitchButton from '@/components/KillSwitchButton';
import PositionTable from '@/components/PositionTable';
import RiskEventLog from '@/components/RiskEventLog';
import { api, useRiskWebSocket } from '@/lib/api';
import { RiskState, RiskConfig, RiskEvent } from '@/lib/types';

export default function DashboardPage() {
  const [riskState, setRiskState] = useState<RiskState | null>(null);
  const [config, setConfig] = useState<RiskConfig | null>(null);
  const [events, setEvents] = useState<RiskEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const [backendConnected, setBackendConnected] = useState(false);

  // Fetch initial data
  const loadData = useCallback(async () => {
    try {
      const [stateRes, cfgRes, evtsRes] = await Promise.allSettled([
        api.fetchRiskState(),
        api.fetchRiskConfig(),
        api.fetchRiskEvents()
      ]);

      if (stateRes.status === 'fulfilled') {
        setRiskState(stateRes.value);
        setBackendConnected(true);
      } else {
        console.warn('Backend risk state fetch failed, using paper state fallback', stateRes.reason);
        setRiskState((prev) => prev || {
          capitalBase: 100000.0,
          dayPnl: 212.50,
          dayPnlPct: 0.21,
          marginUtilisationPct: 15.0,
          positions: [
            {
              symbol: "NIFTY26JUL2619800CE",
              exchange: "NFO",
              qty: 50,
              avgPrice: 120.50,
              ltp: 125.75,
              pnl: 262.50,
              productType: "CARRYFORWARD",
              instrumentType: "CE",
              exposure: 6287.50,
              concentrationPct: 6.29
            },
            {
              symbol: "RELIANCE-EQ",
              exchange: "NSE",
              qty: 10,
              avgPrice: 2450.00,
              ltp: 2445.00,
              pnl: -50.00,
              productType: "INTRADAY",
              instrumentType: "EQ",
              exposure: 24450.00,
              concentrationPct: 24.45
            }
          ],
          activeBreakers: [],
          riskLevel: 'safe',
          killSwitchActive: false,
          paperMode: true,
          lastUpdated: new Date().toISOString()
        });
      }

      if (cfgRes.status === 'fulfilled') {
        setConfig(cfgRes.value);
      } else {
        setConfig((prev) => prev || {
          maxDailyLossPct: 2.0,
          maxPositionConcentrationPct: 20.0,
          maxMarginUtilisationPct: 70.0,
          kellyFractionMultiplier: 0.3,
          orderVelocityLimitPer10Min: 5,
          expiryDaySizeDampener: 0.5
        });
      }

      if (evtsRes.status === 'fulfilled') {
        setEvents(evtsRes.value);
      }
    } catch (err) {
      console.error('Failed to load dashboard data', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    // HTTP polling every 30s as dead-man fallback (WS handles freshness)
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  // Connect to live updates via WebSocket
  const handleLiveStateUpdate = useCallback((liveState: RiskState) => {
    setRiskState((prev) => {
      if (!prev) return liveState;
      return {
        ...prev,
        ...liveState,
        positions: liveState.positions || prev.positions
      };
    });
    
    // Refresh events on new state to capture fresh logs
    api.fetchRiskEvents().then(setEvents).catch(console.error);
  }, []);

  const wsStatus = useRiskWebSocket(handleLiveStateUpdate);

  const handleKillSwitchTriggered = () => {
    loadData();
  };

  if (loading || !riskState || !config) {
    return (
      <div style={styles.skeletonContainer}>
        <div style={styles.skeletonHeader}>
          <div style={styles.skeletonTitle} className="text-gradient">Shield Guard Active...</div>
          <div style={styles.skeletonStatus}>Connecting to Kavach live feed...</div>
        </div>
        <div style={styles.skeletonGrid}>
          <div className="glass-card" style={styles.skeletonCard}></div>
          <div className="glass-card" style={styles.skeletonCard}></div>
          <div className="glass-card" style={styles.skeletonCard}></div>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div>
          <h2 style={styles.title} className="text-gradient">Risk Control Dashboard</h2>
          <p style={styles.subtitle}>
            Live monitoring for retail option trading accounts
          </p>
        </div>
        <div style={styles.connectionBox}>
          <span style={{
            ...styles.indicatorDot,
            backgroundColor:
              wsStatus === 'live' ? '#10b981' :
              wsStatus === 'reconnecting' ? '#f59e0b' :
              backendConnected ? '#3b82f6' : '#ef4444',
            animation: wsStatus === 'reconnecting' ? 'pulse 1.5s ease-in-out infinite' : undefined,
          }} />
          <span style={styles.connectionText}>
            {wsStatus === 'live'
              ? 'LIVE FEED CONNECTED'
              : wsStatus === 'reconnecting'
              ? 'RECONNECTING…'
              : backendConnected
              ? 'POLLING FALLBACK'
              : 'BACKEND OFFLINE'}
          </span>
        </div>
      </header>

      {/* Top metrics section */}
      <section style={styles.topSection}>
        <PnLCard
          dayPnl={riskState.dayPnl}
          dayPnlPct={riskState.dayPnlPct}
          capitalBase={riskState.capitalBase}
          maxDailyLossPct={config.maxDailyLossPct}
        />
        <RiskMeter
          marginUtilisationPct={riskState.marginUtilisationPct}
          activeBreakers={riskState.activeBreakers}
          riskLevel={riskState.riskLevel}
        />
        <KillSwitchButton
          killSwitchActive={riskState.killSwitchActive}
          paperMode={riskState.paperMode}
          onTriggered={handleKillSwitchTriggered}
        />
      </section>

      {/* Main position table */}
      <section style={styles.midSection}>
        <PositionTable positions={riskState.positions} />
      </section>

      {/* Log events list */}
      <section style={styles.bottomSection}>
        <RiskEventLog events={events} />
      </section>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '30px'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottom: '1px solid rgba(255,255,255,0.05)',
    paddingBottom: '20px'
  },
  title: {
    fontSize: '2rem',
    fontWeight: '800',
    letterSpacing: '-0.5px'
  },
  subtitle: {
    fontSize: '0.9rem',
    color: '#64748b',
    marginTop: '4px'
  },
  connectionBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    backgroundColor: 'rgba(255,255,255,0.02)',
    border: '1px solid rgba(255,255,255,0.05)',
    padding: '8px 16px',
    borderRadius: '30px'
  },
  indicatorDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    boxShadow: '0 0 8px currentColor'
  },
  connectionText: {
    fontSize: '0.75rem',
    fontWeight: '700',
    color: '#94a3b8',
    letterSpacing: '0.5px'
  },
  topSection: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '24px',
    width: '100%'
  },
  midSection: {
    width: '100%'
  },
  bottomSection: {
    width: '100%'
  },
  
  // Skeleton / Loader styles
  skeletonContainer: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '80vh',
    gap: '30px'
  },
  skeletonHeader: {
    textAlign: 'center'
  },
  skeletonTitle: {
    fontSize: '1.5rem',
    fontWeight: '700'
  },
  skeletonStatus: {
    fontSize: '0.85rem',
    color: '#64748b',
    marginTop: '6px'
  },
  skeletonGrid: {
    display: 'flex',
    gap: '24px',
    width: '100%',
    maxWidth: '900px'
  },
  skeletonCard: {
    height: '250px',
    flex: 1,
    opacity: 0.5,
    backgroundImage: 'linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.06) 37%, rgba(255,255,255,0.03) 63%)',
    backgroundSize: '400% 100%',
    animation: 'shimmer 1.4s ease infinite'
  }
};

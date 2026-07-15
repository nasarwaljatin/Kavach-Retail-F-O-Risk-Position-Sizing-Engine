'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { RiskConfig, SizingResult } from '@/lib/types';

export default function SettingsPage() {
  // Risk settings config state
  const [config, setConfig] = useState<RiskConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  
  // Position Sizing Calculator state
  const [calcInputs, setCalcInputs] = useState({
    capital: 100000,
    winRate: 0.55,
    avgWin: 1500,
    avgLoss: 1000,
    atr: 35.0,
    riskPerTradePct: 1.0,
    kellyMultiplier: 0.3,
    stopDistanceMultiple: 1.5,
    lotSize: 50
  });
  const [calcResult, setCalcResult] = useState<SizingResult | null>(null);
  const [calculating, setCalculating] = useState(false);

  useEffect(() => {
    // Load config from backend
    api.fetchRiskConfig().then(setConfig).catch(console.error);
  }, []);

  const handleConfigChange = (key: keyof RiskConfig, value: number) => {
    if (!config) return;
    setConfig({
      ...config,
      [key]: value
    });
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!config) return;
    setSaving(true);
    setSaveSuccess(false);
    try {
      await api.updateRiskConfig(config);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      alert('Failed to save settings: ' + (err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleCalculateSize = async () => {
    setCalculating(true);
    try {
      const res = await api.computePositionSize(calcInputs);
      setCalcResult(res);
    } catch (err) {
      alert('Sizing calculation failed: ' + (err as Error).message);
    } finally {
      setCalculating(false);
    }
  };

  if (!config) {
    return <div style={{ color: '#94a3b8', padding: '20px' }}>Loading settings profile...</div>;
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h2 style={styles.title} className="text-gradient">Risk & Sizing Settings</h2>
        <p style={styles.subtitle}>Configure circuit breakers and calculate optimal position weights</p>
      </header>

      <div style={styles.grid}>
        {/* Risk Config Card */}
        <div className="glass-card" style={styles.card}>
          <h3 style={styles.sectionTitle}>🛡️ Risk Engine Limits</h3>
          <form onSubmit={handleSaveConfig} style={styles.form}>
            <div className="form-group">
              <label className="form-label">Max Daily Loss (%)</label>
              <div className="form-desc">Trigger absolute account square-off when daily loss exceeds this.</div>
              <div style={styles.rangeRow}>
                <input 
                  type="range" 
                  min="0.5" 
                  max="10.0" 
                  step="0.5"
                  value={config.maxDailyLossPct}
                  onChange={(e) => handleConfigChange('maxDailyLossPct', parseFloat(e.target.value))}
                  style={styles.slider}
                />
                <span style={styles.badgeVal}>{config.maxDailyLossPct}%</span>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Max Position Concentration (%)</label>
              <div className="form-desc">Block/warn if exposure on any single asset exceeds this % of total capital.</div>
              <div style={styles.rangeRow}>
                <input 
                  type="range" 
                  min="5" 
                  max="50" 
                  step="1"
                  value={config.maxPositionConcentrationPct}
                  onChange={(e) => handleConfigChange('maxPositionConcentrationPct', parseFloat(e.target.value))}
                  style={styles.slider}
                />
                <span style={styles.badgeVal}>{config.maxPositionConcentrationPct}%</span>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Max Margin Utilisation (%)</label>
              <div className="form-desc">Square off positions if utilized funds exceed this ratio.</div>
              <div style={styles.rangeRow}>
                <input 
                  type="range" 
                  min="20" 
                  max="100" 
                  step="5"
                  value={config.maxMarginUtilisationPct}
                  onChange={(e) => handleConfigChange('maxMarginUtilisationPct', parseFloat(e.target.value))}
                  style={styles.slider}
                />
                <span style={styles.badgeVal}>{config.maxMarginUtilisationPct}%</span>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Kelly Fraction Multiplier</label>
              <div className="form-desc">Fraction of full Kelly edge formula to use (e.g. 0.3 for conservative).</div>
              <div style={styles.rangeRow}>
                <input 
                  type="range" 
                  min="0.1" 
                  max="1.0" 
                  step="0.05"
                  value={config.kellyFractionMultiplier}
                  onChange={(e) => handleConfigChange('kellyFractionMultiplier', parseFloat(e.target.value))}
                  style={styles.slider}
                />
                <span style={styles.badgeVal}>{config.kellyFractionMultiplier}</span>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Order Velocity Limit (Per 10 Min)</label>
              <div className="form-desc">Limit on order triggers within 10 minutes to prevent emotional/revenge trading.</div>
              <input 
                type="number" 
                className="form-input"
                min="1"
                max="30"
                value={config.orderVelocityLimitPer10Min}
                onChange={(e) => handleConfigChange('orderVelocityLimitPer10Min', parseInt(e.target.value))}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Expiry Day Size Dampener</label>
              <div className="form-desc">Dampen position sizes on contract expiry days to curb high-volatility loss spikes.</div>
              <div style={styles.rangeRow}>
                <input 
                  type="range" 
                  min="0.1" 
                  max="1.0" 
                  step="0.05"
                  value={config.expiryDaySizeDampener}
                  onChange={(e) => handleConfigChange('expiryDaySizeDampener', parseFloat(e.target.value))}
                  style={styles.slider}
                />
                <span style={styles.badgeVal}>{config.expiryDaySizeDampener}</span>
              </div>
            </div>

            <div style={styles.actionRow}>
              {saveSuccess && <span style={styles.successText}>✓ Config saved!</span>}
              <button className="btn btn-primary" type="submit" disabled={saving}>
                {saving ? 'Saving...' : 'Save Configuration'}
              </button>
            </div>
          </form>
        </div>

        {/* Position Sizer Calculator Playground Card */}
        <div className="glass-card" style={styles.card}>
          <h3 style={styles.sectionTitle}>📊 Sizing Playground (Kelly + ATR)</h3>
          <div style={styles.form}>
            <div style={styles.calcGrid}>
              <div className="form-group">
                <label className="form-label">Capital (INR)</label>
                <input 
                  type="number" 
                  className="form-input" 
                  value={calcInputs.capital}
                  onChange={(e) => setCalcInputs({ ...calcInputs, capital: parseFloat(e.target.value) })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Win Rate (0.0 to 1.0)</label>
                <input 
                  type="number" 
                  step="0.05"
                  className="form-input" 
                  value={calcInputs.winRate}
                  onChange={(e) => setCalcInputs({ ...calcInputs, winRate: parseFloat(e.target.value) })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Avg Win Amount</label>
                <input 
                  type="number" 
                  className="form-input" 
                  value={calcInputs.avgWin}
                  onChange={(e) => setCalcInputs({ ...calcInputs, avgWin: parseFloat(e.target.value) })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Avg Loss Amount</label>
                <input 
                  type="number" 
                  className="form-input" 
                  value={calcInputs.avgLoss}
                  onChange={(e) => setCalcInputs({ ...calcInputs, avgLoss: parseFloat(e.target.value) })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">ATR (Volatility)</label>
                <input 
                  type="number" 
                  className="form-input" 
                  value={calcInputs.atr}
                  onChange={(e) => setCalcInputs({ ...calcInputs, atr: parseFloat(e.target.value) })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Lot Size (Qty)</label>
                <input 
                  type="number" 
                  className="form-input" 
                  value={calcInputs.lotSize}
                  onChange={(e) => setCalcInputs({ ...calcInputs, lotSize: parseInt(e.target.value) })}
                />
              </div>
            </div>

            <button 
              className="btn btn-secondary" 
              style={{ width: '100%', padding: '12px', marginTop: '10px' }}
              onClick={handleCalculateSize}
              disabled={calculating}
            >
              {calculating ? 'Calculating...' : 'Calculate Optimal Size'}
            </button>

            {calcResult && (
              <div style={styles.resultsBox}>
                <h4 style={styles.resultsTitle}>Calculation Output</h4>
                <div style={styles.resultsGrid}>
                  <div style={styles.resultRow}>
                    <span style={styles.resultLabel}>Kelly Quantity:</span>
                    <span style={styles.resultVal}>{calcResult.kellyQty}</span>
                  </div>
                  <div style={styles.resultRow}>
                    <span style={styles.resultLabel}>Vol-Adjusted Quantity:</span>
                    <span style={styles.resultVal}>{calcResult.volAdjustedQty}</span>
                  </div>
                  <div style={styles.resultRow}>
                    <span style={styles.resultLabel}>Recommended Quantity:</span>
                    <span style={{ ...styles.resultVal, color: '#3b82f6', fontWeight: '700' }}>
                      {calcResult.recommendedQty}
                    </span>
                  </div>
                  <div style={{ ...styles.resultRow, borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '10px', marginTop: '10px' }}>
                    <span style={styles.resultLabel}>Recommended Lots:</span>
                    <span style={{ ...styles.resultVal, color: '#10b981', fontWeight: '800' }}>
                      {calcResult.lots} Lots ({calcResult.totalQty} total shares)
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
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
  grid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '30px'
  },
  card: {
    flex: '1 1 450px',
    maxWidth: '100%'
  },
  sectionTitle: {
    fontSize: '1.1rem',
    fontWeight: '700',
    color: '#f8fafc',
    marginBottom: '24px'
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px'
  },
  rangeRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px'
  },
  slider: {
    flexGrow: 1,
    accentColor: '#3b82f6'
  },
  badgeVal: {
    minWidth: '60px',
    textAlign: 'right',
    fontFamily: 'monospace',
    fontWeight: '700',
    fontSize: '0.95rem',
    color: '#3b82f6'
  },
  actionRow: {
    display: 'flex',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: '16px',
    marginTop: '20px'
  },
  successText: {
    color: '#10b981',
    fontWeight: '600',
    fontSize: '0.9rem'
  },
  calcGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '16px'
  },
  resultsBox: {
    marginTop: '24px',
    backgroundColor: 'rgba(59, 130, 246, 0.03)',
    border: '1px solid rgba(59, 130, 246, 0.1)',
    borderRadius: '12px',
    padding: '20px'
  },
  resultsTitle: {
    color: '#3b82f6',
    fontWeight: '700',
    fontSize: '0.95rem',
    marginBottom: '16px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  resultsGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px'
  },
  resultRow: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.85rem'
  },
  resultLabel: {
    color: '#94a3b8'
  },
  resultVal: {
    color: '#f8fafc',
    fontWeight: '600',
    fontFamily: 'monospace'
  }
};

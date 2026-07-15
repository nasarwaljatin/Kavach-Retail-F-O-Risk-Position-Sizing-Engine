'use client';

import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';

interface KillSwitchButtonProps {
  killSwitchActive: boolean;
  paperMode: boolean;
  onTriggered: () => void;
}

export default function KillSwitchButton({ killSwitchActive, paperMode, onTriggered }: KillSwitchButtonProps) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (cooldown > 0) {
      timer = setTimeout(() => setCooldown(cooldown - 1), 1000);
    }
    return () => clearTimeout(timer);
  }, [cooldown]);

  const handleTrigger = async () => {
    setLoading(true);
    try {
      await api.triggerKillSwitch();
      onTriggered();
      setCooldown(30); // 30 second cooldown
      setShowConfirm(false);
    } catch (err) {
      alert('Error triggering emergency square-off: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-card" style={styles.card}>
      <div style={styles.header}>
        <span style={styles.title}>Emergency Square-Off</span>
        <span style={{
          ...styles.dot,
          backgroundColor: killSwitchActive ? '#ef4444' : '#10b981',
          boxShadow: `0 0 8px ${killSwitchActive ? '#ef4444' : '#10b981'}`
        }}></span>
      </div>

      <div style={styles.content}>
        <p style={styles.description}>
          Immediately square-off all active open positions using market orders.
        </p>

        {cooldown > 0 ? (
          <button className="btn" disabled style={{ ...styles.killBtn, backgroundColor: '#334155', color: '#94a3b8' }}>
            COOLDOWN ({cooldown}s)
          </button>
        ) : killSwitchActive ? (
          <button className="btn" disabled style={{ ...styles.killBtn, backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
            LOCKED (SQUARED-OFF)
          </button>
        ) : (
          <button 
            className="btn btn-danger pulse-danger" 
            style={styles.killBtn}
            onClick={() => setShowConfirm(true)}
          >
            🔥 ACTIVATE KILL SWITCH
          </button>
        )}
      </div>

      {showConfirm && (
        <div style={styles.modalOverlay}>
          <div className="glass-card" style={styles.modalCard}>
            <h3 style={styles.modalTitle}>⚠️ Confirm Emergency Square-Off</h3>
            <p style={styles.modalBody}>
              Are you sure you want to exit all open positions? This will place immediate market orders to close all positions.
              {paperMode && <strong style={{ display: 'block', color: '#f59e0b', marginTop: '8px' }}>Note: Running in PAPER MODE (orders will be simulated).</strong>}
            </p>
            <div style={styles.modalActions}>
              <button 
                className="btn btn-secondary" 
                onClick={() => setShowConfirm(false)}
                disabled={loading}
              >
                Cancel
              </button>
              <button 
                className="btn btn-danger" 
                onClick={handleTrigger}
                disabled={loading}
              >
                {loading ? 'Executing...' : 'Yes, Square-Off All'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    flex: 1,
    minWidth: '280px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    position: 'relative'
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
  dot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    transition: 'all 0.3s ease'
  },
  content: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
    height: '100%',
    justifyContent: 'space-between'
  },
  description: {
    fontSize: '0.85rem',
    color: '#94a3b8',
    lineHeight: '1.4'
  },
  killBtn: {
    width: '100%',
    padding: '16px',
    fontSize: '0.95rem',
    letterSpacing: '0.5px'
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
    backdropFilter: 'blur(4px)'
  },
  modalCard: {
    width: '450px',
    maxWidth: '90%',
    backgroundColor: '#0c1224',
    border: '1px solid rgba(239, 68, 68, 0.2)',
    boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
    padding: '30px'
  },
  modalTitle: {
    color: '#ef4444',
    marginBottom: '12px',
    fontSize: '1.2rem',
    fontWeight: '700'
  },
  modalBody: {
    color: '#94a3b8',
    fontSize: '0.9rem',
    marginBottom: '24px',
    lineHeight: '1.5'
  },
  modalActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px'
  }
};

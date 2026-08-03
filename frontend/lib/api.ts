import { useState, useEffect, useRef } from 'react';
import { RiskState, RiskConfig, RiskEvent, DailySummary, SizingResult, Position } from './types';

// Detect browser environment base API URLs
// Detect browser environment base API URLs
export function getApiBase(): string {
  if (typeof window !== 'undefined') {
    const custom = localStorage.getItem('KAVACH_API_URL');
    if (custom && custom.trim() !== '') {
      return custom.trim().replace(/\/$/, '');
    }
  }
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '');
  }
  return typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000';
}

export function setApiBase(url: string): void {
  if (typeof window !== 'undefined') {
    if (!url || url.trim() === '') {
      localStorage.removeItem('KAVACH_API_URL');
    } else {
      localStorage.setItem('KAVACH_API_URL', url.trim().replace(/\/$/, ''));
    }
  }
}

export function getWsBase(): string {
  const apiBase = getApiBase();
  try {
    const url = new URL(apiBase);
    const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//${url.host}`;
  } catch (e) {
    return typeof window !== 'undefined'
      ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
      : 'ws://localhost:8000';
  }
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || `API error: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async testConnection(url: string): Promise<boolean> {
    try {
      const cleanUrl = url.trim().replace(/\/$/, '');
      const res = await fetch(`${cleanUrl}/health`, { method: 'GET' });
      return res.ok;
    } catch {
      return false;
    }
  },

  async fetchLivePositions(): Promise<Position[]> {
    return fetchJson<Position[]>(`${getApiBase()}/api/positions/`);
  },

  async fetchRiskState(): Promise<RiskState> {
    const state = await fetchJson<any>(`${getApiBase()}/api/risk/state`);
    const positions = await this.fetchLivePositions();
    return {
      ...state,
      positions,
      activeBreakers: state.activeBreakers || [],
      paperMode: true // default fallback
    };
  },

  async fetchRiskEvents(): Promise<RiskEvent[]> {
    return fetchJson<RiskEvent[]>(`${getApiBase()}/api/risk/events`);
  },

  async fetchRiskConfig(): Promise<RiskConfig> {
    return fetchJson<RiskConfig>(`${getApiBase()}/api/risk/config`);
  },

  async updateRiskConfig(config: Partial<RiskConfig>): Promise<{ status: string; message: string }> {
    return fetchJson<{ status: string; message: string }>(`${getApiBase()}/api/risk/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
  },

  async triggerKillSwitch(): Promise<{ status: string; message: string; orders_placed: number }> {
    return fetchJson<{ status: string; message: string; orders_placed: number }>(`${getApiBase()}/api/killswitch/`, {
      method: 'POST'
    });
  },

  async fetchDailySummary(): Promise<DailySummary[]> {
    return fetchJson<DailySummary[]>(`${getApiBase()}/api/dashboard/summary`);
  },

  async computePositionSize(params: {
    capital: number;
    winRate: number;
    avgWin: number;
    avgLoss: number;
    atr: number;
    riskPerTradePct?: number;
    kellyMultiplier?: number;
    stopDistanceMultiple?: number;
    lotSize?: number;
  }): Promise<SizingResult> {
    return fetchJson<SizingResult>(`${getApiBase()}/api/risk/size`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
  }
};

export function useRiskWebSocket(onMessage: (state: RiskState) => void): 'live' | 'reconnecting' | 'disconnected' {
  const [wsStatus, setWsStatus] = useState<'live' | 'reconnecting' | 'disconnected'>('disconnected');
  const socketRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const onMessageRef = useRef(onMessage);

  // Keep callback ref current without re-running effect
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    mountedRef.current = true;

    function getWsUrl(): string {
      let base = `${getWsBase()}/ws/risk`;
      // Dev convenience: if WS base still points to the Next.js dev port, redirect to backend
      if (base.includes(':3000')) base = base.replace(':3000', ':8000');
      return base;
    }

    function connect() {
      if (!mountedRef.current) return;

      try {
        const ws = new WebSocket(getWsUrl());
        socketRef.current = ws;

        ws.onopen = () => {
          if (!mountedRef.current) return;
          retryCountRef.current = 0;
          setWsStatus('live');
          console.info('[Kavach WS] Connected to live risk stream.');
        };

        ws.onmessage = (event) => {
          if (!mountedRef.current) return;
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'ACK') return; // connection ack, ignore
            onMessageRef.current(data as RiskState);
          } catch (err) {
            console.error('[Kavach WS] Failed to parse message:', err);
          }
        };

        ws.onclose = () => {
          if (!mountedRef.current) return;
          setWsStatus('reconnecting');
          scheduleReconnect();
        };

        ws.onerror = () => {
          // onclose fires after onerror, so just log here
          console.warn('[Kavach WS] Socket error — will attempt reconnect.');
        };
      } catch (err) {
        console.error('[Kavach WS] Failed to open socket:', err);
        setWsStatus('reconnecting');
        scheduleReconnect();
      }
    }

    function scheduleReconnect() {
      if (!mountedRef.current) return;
      // Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 30s
      const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30_000);
      retryCountRef.current += 1;
      console.info(`[Kavach WS] Reconnecting in ${delay / 1000}s (attempt ${retryCountRef.current})...`);
      retryTimerRef.current = setTimeout(connect, delay);
    }

    connect();

    return () => {
      mountedRef.current = false;
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      if (socketRef.current) {
        socketRef.current.onclose = null; // prevent reconnect loop on intentional unmount
        socketRef.current.close();
      }
      setWsStatus('disconnected');
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run once on mount — reconnect is handled internally

  return wsStatus;
}

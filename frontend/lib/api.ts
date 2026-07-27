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

export function useRiskWebSocket(onMessage: (state: RiskState) => void) {
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let wsUrl = `${getWsBase()}/ws/risk`;
    // If proxied locally during development, resolve port
    if (wsUrl.includes('3000')) {
      wsUrl = wsUrl.replace('3000', '8000');
    }
    
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setConnected(true);
      console.log('Kavach live stream connected.');
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'ACK') {
          return;
        }
        onMessage(data as RiskState);
      } catch (err) {
        console.error('Failed to parse WebSocket message', err);
      }
    };

    socket.onclose = () => {
      setConnected(false);
      console.log('Kavach live stream disconnected.');
    };

    socket.onerror = (error) => {
      console.error('WebSocket error', error);
    };

    return () => {
      socket.close();
    };
  }, [onMessage]);

  return connected;
}

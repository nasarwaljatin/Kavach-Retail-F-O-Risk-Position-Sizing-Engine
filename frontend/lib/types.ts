export interface Position {
  symbol: string;
  exchange: string;
  qty: number;
  avgPrice: number;
  ltp: number;
  pnl: number;
  productType: string;
  instrumentType: string;
  exposure: number;
  concentrationPct: number;
}

export interface RiskState {
  capitalBase: number;
  dayPnl: number;
  dayPnlPct: number;
  marginUtilisationPct: number;
  positions: Position[];
  activeBreakers: string[];
  riskLevel: 'safe' | 'warning' | 'danger';
  killSwitchActive: boolean;
  paperMode: boolean;
  lastUpdated: string;
}

export interface RiskConfig {
  maxDailyLossPct: number;
  maxPositionConcentrationPct: number;
  maxMarginUtilisationPct: number;
  kellyFractionMultiplier: number;
  orderVelocityLimitPer10Min: number;
  expiryDaySizeDampener: number;
}

export interface RiskEvent {
  id: number;
  ts: string;
  breakerType: string;
  details: string;
  actionTaken: string;
}

export interface DailySummary {
  date: string;
  capitalBase: number;
  realizedPnl: number;
  unrealizedPnl: number;
  maxDrawdown: number;
  breakerTriggers: number;
}

export interface SizingResult {
  kellyQty: number;
  volAdjustedQty: number;
  recommendedQty: number;
  lots: number;
  totalQty: number;
}

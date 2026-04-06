/**
 * Session Intelligence Store (v4)
 * 
 * Central session state manager using sessionStorage + localStorage (offline backup).
 * Tracks user navigation, recently accessed items, time-on-page, heuristics, and transitions.
 * Adaptive Self-Tuning: Learns from prediction hits/misses and decays old data.
 * 
 * Version History:
 *   v1 — Added version field, lastOpenedFile tracking, migration from legacy key
 *   v2 — Added heuristic tracking (pageVisits, fileOpens, timeSpent), debounced storage, silent debug
 *   v3 — Added transitionMap for prediction, offline-first localStorage mirroring
 *   v4 — Added adaptive scoring (decay), confidence thresholds, feedback loops, multi-tab sync
 */

const SESSION_KEY = 'rims_session_v4';
const LEGACY_KEY_V3 = 'rims_session_v3';
const LEGACY_KEY_V2 = 'rims_session_v2';
const LEGACY_KEY_V1 = 'rims_session_v1';
const LEGACY_KEY_V0 = 'rims_session';
const OFFLINE_CACHE_KEY = 'rims_offline_cache_v4';

const DEBUG = process.env.NODE_ENV === 'development';

export interface SessionData {
  version: 4;
  lastVisitedPage: string;
  lastOpenedFile: { name: string; path: string; timestamp: number } | null;
  recentPages: { path: string; title: string; timestamp: number }[];
  
  // Heuristics (upgraded to include lastVisited timestamps for decay)
  pageVisits: Record<string, { count: number, lastVisited: number }>;
  fileOpens: Record<string, { count: number, lastVisited: number }>;
  timeSpent: Record<string, number>;
  transitionMap: Record<string, Record<string, number>>;
  
  // Adaptive Self-Tuning (v4)
  predictionsMeta: { hits: number, misses: number };
  weights: { recency: number, frequency: number, transition: number };
  
  sessionStartedAt: number;
  lastActivityAt: number;
}

const DEFAULT_SESSION_V4: SessionData = {
  version: 4,
  lastVisitedPage: '/dashboard/hr',
  lastOpenedFile: null,
  recentPages: [],
  pageVisits: {},
  fileOpens: {},
  timeSpent: {},
  transitionMap: {},
  predictionsMeta: { hits: 0, misses: 0 },
  weights: { recency: 1.0, frequency: 1.0, transition: 2.0 }, // Defaults
  sessionStartedAt: typeof window !== 'undefined' ? Date.now() : 0,
  lastActivityAt: typeof window !== 'undefined' ? Date.now() : 0,
};

const MAX_RECENT_PAGES = 10;
let saveTimeout: NodeJS.Timeout | null = null;
let _cachedSession: SessionData | null = null; // Memory cache for multi-tab sync

/**
 * Initialize Multi-Tab Sync.
 * If another tab saves a fresh session, we silently merge it to prevent stale overwrites.
 */
if (typeof window !== 'undefined') {
  window.addEventListener('storage', (e) => {
    if (e.key === SESSION_KEY && e.newValue) {
      try {
        const remoteSession = JSON.parse(e.newValue);
        if (_cachedSession && remoteSession.lastActivityAt > _cachedSession.lastActivityAt) {
           _cachedSession = remoteSession;
           if (DEBUG) console.debug('[Session v4] Synced state from another tab.');
        }
      } catch { /* Ignore */ }
    }
  });
}

/**
 * Cascade migration from v3, v2, v1, or v0.
 */
function migrateFromLegacy(): SessionData | null {
  if (typeof window === 'undefined') return null;

  try {
    const offlineRaw = localStorage.getItem(OFFLINE_CACHE_KEY);
    if (offlineRaw) {
      const parsed = JSON.parse(offlineRaw);
      if (parsed.version === 4) return parsed as SessionData; 
    }

    let raw = sessionStorage.getItem(LEGACY_KEY_V3);
    if (!raw) {
      raw = sessionStorage.getItem(LEGACY_KEY_V2);
      if (!raw) {
        raw = sessionStorage.getItem(LEGACY_KEY_V1);
        if (!raw) {
          raw = sessionStorage.getItem(LEGACY_KEY_V0);
          if (!raw) return null;
          sessionStorage.removeItem(LEGACY_KEY_V0);
        } else {
          sessionStorage.removeItem(LEGACY_KEY_V1);
        }
      } else {
        sessionStorage.removeItem(LEGACY_KEY_V2);
      }
    } else {
      sessionStorage.removeItem(LEGACY_KEY_V3);
      localStorage.removeItem('rims_offline_cache_v3');
    }

    const old = JSON.parse(raw) as any;
    
    // Map existing structure into V4 gracefully
    const pageVisits: Record<string, { count: number, lastVisited: number }> = {};
    if (old.pageVisits) {
      Object.entries(old.pageVisits).forEach(([path, val]) => {
        if (typeof val === 'number') {
           pageVisits[path] = { count: val, lastVisited: old.lastActivityAt || Date.now() };
        } else {
           pageVisits[path] = val as any;
        }
      });
    }

    const fileOpens: Record<string, { count: number, lastVisited: number }> = {};
    if (old.fileOpens) {
      Object.entries(old.fileOpens).forEach(([path, val]) => {
        if (typeof val === 'number') {
           fileOpens[path] = { count: val, lastVisited: old.lastActivityAt || Date.now() };
        } else {
           fileOpens[path] = val as any;
        }
      });
    }

    return {
      ...DEFAULT_SESSION_V4,
      lastVisitedPage: old.lastVisitedPage || DEFAULT_SESSION_V4.lastVisitedPage,
      recentPages: Array.isArray(old.recentPages) ? old.recentPages : [],
      sessionStartedAt: old.sessionStartedAt || Date.now(),
      lastActivityAt: old.lastActivityAt || Date.now(),
      lastOpenedFile: old.lastOpenedFile || null,
      pageVisits,
      fileOpens,
      timeSpent: old.timeSpent || {},
      transitionMap: old.transitionMap || {},
      predictionsMeta: old.predictionsMeta || { hits: 0, misses: 0 },
      weights: old.weights || { recency: 1.0, frequency: 1.0, transition: 2.0 },
      version: 4,
    };
  } catch {
    [LEGACY_KEY_V3, LEGACY_KEY_V2, LEGACY_KEY_V1, LEGACY_KEY_V0].forEach(k => sessionStorage.removeItem(k));
    return null;
  }
}

/**
 * Get the current session data.
 */
export function getSessionData(): SessionData {
  if (typeof window === 'undefined') return { ...DEFAULT_SESSION_V4 };
  if (_cachedSession) return _cachedSession;

  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed.version === 4) {
        _cachedSession = parsed;
        return parsed as SessionData;
      }
    }

    const migrated = migrateFromLegacy();
    if (migrated) {
      saveSession(migrated);
      return migrated;
    }

    return { ...DEFAULT_SESSION_V4, sessionStartedAt: Date.now(), lastActivityAt: Date.now() };
  } catch {
    return { ...DEFAULT_SESSION_V4, sessionStartedAt: Date.now(), lastActivityAt: Date.now() };
  }
}

export interface PredictionWithConfidence {
  path: string;
  score: number;
  confidence: number;
}

/**
 * Adaptive Scoring Engine (Decay + Dynamic Weights)
 */
export function getPredictedNextPages(currentPath: string, session?: SessionData): PredictionWithConfidence[] {
  const s = session || getSessionData();
  const transitions = s.transitionMap[currentPath] || {};
  const { pageVisits, weights } = s;
  
  const now = Date.now();
  const decayRate = 0.05; // 5% decay per day

  const scores: Record<string, number> = {};
  
  // 1. Contextual Transitions (Heaviest Weight)
  Object.entries(transitions).forEach(([nextPath, count]) => {
    scores[nextPath] = (scores[nextPath] || 0) + (count * weights.transition); 
  });
  
  // 2. Global Frequency with Exponential Time Decay
  Object.entries(pageVisits).forEach(([path, data]) => {
    if (path !== currentPath) {
      const daysOld = Math.max((now - data.lastVisited) / (1000 * 60 * 60 * 24), 0);
      const decayedScore = data.count * Math.exp(-decayRate * daysOld);
      scores[path] = (scores[path] || 0) + (decayedScore * weights.frequency);
    }
  });

  return Object.entries(scores)
    .map(([path, score]) => {
       // Normalize confidence (0 to 1). 50 is a heuristic "high confidence" benchmark score.
       const confidence = Math.min(score / 50.0, 1.0);
       return { path, score, confidence };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);
}

/**
 * Feedback Loop: Evaluates prediction accuracy and tunes weights.
 */
export function evaluatePredictionAccuracy(actualPath: string, previousPath: string): void {
  if (typeof window === 'undefined') return;
  const session = getSessionData();
  
  const predictions = getPredictedNextPages(previousPath, session);
  const topPrediction = predictions[0]?.path;
  
  if (topPrediction === actualPath) {
    session.predictionsMeta.hits += 1;
    // Reward transition weight (cap at 5.0)
    session.weights.transition = Math.min(session.weights.transition + 0.1, 5.0);
    if (DEBUG) console.debug(`[Session v4] Prediction HIT. Increased transition weight to ${session.weights.transition.toFixed(2)}`);
  } else if (topPrediction) {
    session.predictionsMeta.misses += 1;
    // Penalize transition weight slightly (floor at 1.0)
    session.weights.transition = Math.max(session.weights.transition - 0.05, 1.0);
    if (DEBUG) console.debug(`[Session v4] Prediction MISS. Decreased transition weight to ${session.weights.transition.toFixed(2)}`);
  }
  
  saveSession(session);
}

export function getMostVisitedPages(session?: SessionData) {
  return getTopItems((session || getSessionData()).pageVisits);
}

export function getMostOpenedFiles(session?: SessionData) {
  return getTopItems((session || getSessionData()).fileOpens);
}

function getTopItems(records: Record<string, { count: number }>, limit: number = 5) {
  return Object.entries(records)
    .sort(([, a], [, b]) => b.count - a.count)
    .slice(0, limit)
    .map(([path, data]) => ({ path, count: data.count }));
}

/**
 * Record a page visit and activity timestamp.
 */
export function recordPageVisit(path: string, title?: string): void {
  if (typeof window === 'undefined') return;

  const session = getSessionData();
  const now = Date.now();

  session.lastVisitedPage = path;
  session.lastActivityAt = now;
  
  if (!session.pageVisits[path]) session.pageVisits[path] = { count: 0, lastVisited: 0 };
  session.pageVisits[path].count += 1;
  session.pageVisits[path].lastVisited = now;

  const filtered = session.recentPages.filter(p => p.path !== path);
  filtered.unshift({ path, title: title || deriveTitle(path), timestamp: now });
  session.recentPages = filtered.slice(0, MAX_RECENT_PAGES);

  saveSession(session);
}

/**
 * Record a contextual transition (A -> B).
 */
export function recordTransition(fromPath: string, toPath: string): void {
  if (typeof window === 'undefined') return;
  if (fromPath === toPath) return;

  const session = getSessionData();
  session.lastActivityAt = Date.now();
  
  if (!session.transitionMap[fromPath]) {
    session.transitionMap[fromPath] = {};
  }
  
  if (Object.keys(session.transitionMap[fromPath]).length >= 10 && !session.transitionMap[fromPath][toPath]) {
    return;
  }

  session.transitionMap[fromPath][toPath] = (session.transitionMap[fromPath][toPath] || 0) + 1;
  saveSession(session);
}

export function recordFileOpen(name: string, path: string): void {
  if (typeof window === 'undefined') return;

  const session = getSessionData();
  const now = Date.now();
  session.lastOpenedFile = { name, path, timestamp: now };
  session.lastActivityAt = now;
  
  if (!session.fileOpens[path]) session.fileOpens[path] = { count: 0, lastVisited: 0 };
  session.fileOpens[path].count += 1;
  session.fileOpens[path].lastVisited = now;

  saveSession(session);
}

export function recordTimeSpent(path: string, durationMs: number): void {
  if (typeof window === 'undefined') return;

  const session = getSessionData();
  session.timeSpent[path] = (session.timeSpent[path] || 0) + durationMs;
  session.lastActivityAt = Date.now();
  saveSession(session);
}

export function getSessionDuration(): number {
  const session = getSessionData();
  return Math.floor((Date.now() - session.sessionStartedAt) / 1000);
}

export function clearSession(): void {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(SESSION_KEY);
  localStorage.removeItem(OFFLINE_CACHE_KEY);
  _cachedSession = null;
  if (DEBUG) console.debug('[Session v4] Session cleared.');
}

// --- Internal helpers ---

function saveSession(session: SessionData): void {
  _cachedSession = session; // Instantly update memory cache
  
  if (saveTimeout) clearTimeout(saveTimeout);
  
  saveTimeout = setTimeout(() => {
    try {
      const data = JSON.stringify(session);
      sessionStorage.setItem(SESSION_KEY, data);
      localStorage.setItem(OFFLINE_CACHE_KEY, data);
    } catch {
      // sessionStorage quota exceeded — silently degrade
    }
  }, 1000);
}

function deriveTitle(path: string): string {
  const segments = path.split('/').filter(Boolean);
  const last = segments[segments.length - 1] || 'Dashboard';
  return last
    .replace(/-/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

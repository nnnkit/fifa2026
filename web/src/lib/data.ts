// Data loader — reads from ../../data/ at build time.
// In dev, reload JSON on each request so newly fetched teams appear without
// restarting the Astro server.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.resolve(__dirname, '../../../data');

export interface TeamMeta {
  slug: string;
  country: string;
  group: string;
  national_team_article: string;
  tournament_article: string;
  wikidata_qid: string;
}

export interface PlayerPhoto {
  filename?: string;
  url?: string;
  thumb_url?: string;
  license?: string;
  license_url?: string;
  attribution?: string;
  local_path?: string;
}

export interface PlayerRecord {
  slug: string;
  display_name: string;
  name?: string;
  shirt_no: number | null;
  position_code: 'GK' | 'DF' | 'MF' | 'FW' | string;
  dob?: string | null;
  date_of_birth?: string | null;
  age?: number | null;
  caps: number;
  goals: number;
  current_club?: string;
  club_from_squad_table?: string;
  positions?: string[];
  citizenship?: string[];
  place_of_birth?: string;
  height_cm?: number;
  weight_kg?: number;
  wikipedia_url?: string;
  wikipedia_title?: string;
  transfermarkt_id?: string | number;
  photo?: PlayerPhoto;
  team_slug?: string;
  team_country?: string;
  description?: string;
  teams?: Array<{ team_qid: string; start: string | null; end: string | null }>;
}

export interface TeamRecord {
  slug: string;
  country: string;
  wikidata_qid: string;
  fetched_at: string;
  source: { kind: string; title: string; url: string };
  squad_size: number;
  players: PlayerRecord[];
  group?: string;
}

export interface ScheduleTeam {
  name: string;
  code: string;
  slug?: string;
  countryCode?: string;
  placeholder?: string;
}

export interface ScheduleMatch {
  matchNumber: number;
  idMatch: string;
  dateUtc: string;
  localDate?: string;
  stage: string;
  group?: string | null;
  home: ScheduleTeam;
  away: ScheduleTeam;
  venue: string;
  city: string;
  countryCode: string;
}

export interface ScheduleData {
  generatedAt: string;
  source: { name: string; url: string; pageUrl: string };
  season: { idCompetition: string; idSeason: string; name: string };
  matches: ScheduleMatch[];
}

let _teamsMeta: TeamMeta[] | null = null;
let _teamsMetaLoadedAt = 0;
let _teamFiles: Map<string, TeamRecord> | null = null;
let _teamFilesLoadedAt = 0;
let _playerFiles: Map<string, PlayerRecord> | null = null;
let _playerFilesLoadedAt = 0;
let _statusFiles: Map<string, StatusOverlay> | null = null;
let _statusFilesLoadedAt = 0;
let _scheduleData: ScheduleData | null = null;
let _scheduleDataLoadedAt = 0;

const CACHE_DATA_FILES = import.meta.env.PROD;
const DEV_DATA_CACHE_MS = 1000;

function isFresh<T>(value: T | null, loadedAt: number): value is T {
  return value !== null && (CACHE_DATA_FILES || Date.now() - loadedAt < DEV_DATA_CACHE_MS);
}

export function getAllTeamMeta(): TeamMeta[] {
  if (isFresh(_teamsMeta, _teamsMetaLoadedAt)) return _teamsMeta;
  const raw = fs.readFileSync(path.join(DATA_DIR, 'teams.json'), 'utf-8');
  _teamsMeta = JSON.parse(raw) as TeamMeta[];
  _teamsMeta.sort((a, b) =>
    a.group === b.group ? a.country.localeCompare(b.country) : a.group.localeCompare(b.group)
  );
  _teamsMetaLoadedAt = Date.now();
  return _teamsMeta;
}

export function getTeamMeta(slug: string): TeamMeta | undefined {
  return getAllTeamMeta().find((t) => t.slug === slug);
}

export function getGroups(): Record<string, TeamMeta[]> {
  const groups: Record<string, TeamMeta[]> = {};
  for (const t of getAllTeamMeta()) {
    (groups[t.group] ??= []).push(t);
  }
  return groups;
}

function loadAllTeamFiles(): Map<string, TeamRecord> {
  if (isFresh(_teamFiles, _teamFilesLoadedAt)) return _teamFiles;
  _teamFiles = new Map();
  const dir = path.join(DATA_DIR, 'teams');
  if (!fs.existsSync(dir)) {
    _teamFilesLoadedAt = Date.now();
    return _teamFiles;
  }
  for (const f of fs.readdirSync(dir)) {
    if (!f.endsWith('.json')) continue;
    const slug = f.replace(/\.json$/, '');
    try {
      const raw = fs.readFileSync(path.join(dir, f), 'utf-8');
      _teamFiles.set(slug, JSON.parse(raw) as TeamRecord);
    } catch {
      // skip malformed
    }
  }
  _teamFilesLoadedAt = Date.now();
  return _teamFiles;
}

export function getTeam(slug: string): TeamRecord | undefined {
  return loadAllTeamFiles().get(slug);
}

export function getPopulatedTeamSlugs(): string[] {
  return Array.from(loadAllTeamFiles().keys());
}

function loadAllPlayerFiles(): Map<string, PlayerRecord> {
  if (isFresh(_playerFiles, _playerFilesLoadedAt)) return _playerFiles;
  _playerFiles = new Map();
  const dir = path.join(DATA_DIR, 'players');
  if (!fs.existsSync(dir)) {
    _playerFilesLoadedAt = Date.now();
    return _playerFiles;
  }
  for (const f of fs.readdirSync(dir)) {
    if (!f.endsWith('.json')) continue;
    const slug = f.replace(/\.json$/, '');
    try {
      const raw = fs.readFileSync(path.join(dir, f), 'utf-8');
      _playerFiles.set(slug, JSON.parse(raw) as PlayerRecord);
    } catch {
      // skip
    }
  }
  _playerFilesLoadedAt = Date.now();
  return _playerFiles;
}

export function getPlayer(slug: string): PlayerRecord | undefined {
  return loadAllPlayerFiles().get(slug);
}

export function getAllPlayers(): PlayerRecord[] {
  return Array.from(loadAllPlayerFiles().values());
}

export function getScheduleData(): ScheduleData {
  if (isFresh(_scheduleData, _scheduleDataLoadedAt)) return _scheduleData;
  const raw = fs.readFileSync(path.join(DATA_DIR, 'schedule.json'), 'utf-8');
  _scheduleData = JSON.parse(raw) as ScheduleData;
  _scheduleData.matches.sort((a, b) =>
    a.dateUtc === b.dateUtc ? a.matchNumber - b.matchNumber : a.dateUtc.localeCompare(b.dateUtc)
  );
  _scheduleDataLoadedAt = Date.now();
  return _scheduleData;
}

export function getAllMatches(): ScheduleMatch[] {
  return getScheduleData().matches;
}

export function getTeamMatches(slug: string): ScheduleMatch[] {
  return getAllMatches().filter((m) => m.home.slug === slug || m.away.slug === slug);
}

export function getNextTeamMatch(slug: string, now: Date = new Date()): ScheduleMatch | undefined {
  return getTeamMatches(slug).find((m) => new Date(m.dateUtc).getTime() >= now.getTime());
}

// ----- derived helpers -----

export function ageFromDob(dob?: string | null, today: Date = new Date()): number | null {
  if (!dob) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(dob);
  if (!m) return null;
  const [, y, mo, d] = m;
  const birth = new Date(Number(y), Number(mo) - 1, Number(d));
  if (isNaN(birth.getTime())) return null;
  let age = today.getFullYear() - birth.getFullYear();
  const m2 = today.getMonth() - birth.getMonth();
  if (m2 < 0 || (m2 === 0 && today.getDate() < birth.getDate())) age--;
  return age;
}

export const POSITION_ORDER: Record<string, number> = { GK: 0, DF: 1, MF: 2, FW: 3 };

export const POSITION_LABEL: Record<string, string> = {
  GK: 'Goalkeepers',
  DF: 'Defenders',
  MF: 'Midfielders',
  FW: 'Forwards',
};

export function sortSquad(players: PlayerRecord[]): PlayerRecord[] {
  return [...players].sort((a, b) => {
    const pa = POSITION_ORDER[a.position_code] ?? 99;
    const pb = POSITION_ORDER[b.position_code] ?? 99;
    if (pa !== pb) return pa - pb;
    const sa = a.shirt_no ?? 999;
    const sb = b.shirt_no ?? 999;
    if (sa !== sb) return sa - sb;
    return a.display_name.localeCompare(b.display_name);
  });
}

export function photoUrl(player: PlayerRecord): string | null {
  if (!player.photo) return null;
  if (player.photo.local_path) {
    const name = player.photo.local_path.split('/').pop();
    return name ? `/photos/${name}` : null;
  }
  return player.photo.thumb_url ?? player.photo.url ?? null;
}

// Status overlay — scanner output is optional and lives in data/status/*.json.
// Never hard-code demo injury/suspension data into production pages.
export interface StatusOverlay {
  status: 'available' | 'yellow' | 'doubtful' | 'injured' | 'suspended';
  reason?: string;
  last_updated?: string;
  source?: { url: string; headline: string };
}

function loadAllStatusFiles(): Map<string, StatusOverlay> {
  if (isFresh(_statusFiles, _statusFilesLoadedAt)) return _statusFiles;
  _statusFiles = new Map();
  const dir = path.join(DATA_DIR, 'status');
  if (!fs.existsSync(dir)) {
    _statusFilesLoadedAt = Date.now();
    return _statusFiles;
  }
  for (const f of fs.readdirSync(dir)) {
    if (!f.endsWith('.json')) continue;
    const slug = f.replace(/\.json$/, '');
    try {
      const raw = fs.readFileSync(path.join(dir, f), 'utf-8');
      _statusFiles.set(slug, JSON.parse(raw) as StatusOverlay);
    } catch {
      // skip malformed status files
    }
  }
  _statusFilesLoadedAt = Date.now();
  return _statusFiles;
}

export function getStatus(slug: string): StatusOverlay {
  return loadAllStatusFiles().get(slug) ?? { status: 'available' };
}

export function getRecentStatusChanges(): Array<{
  player: PlayerRecord;
  status: StatusOverlay;
}> {
  const out: Array<{ player: PlayerRecord; status: StatusOverlay }> = [];
  for (const [slug, status] of loadAllStatusFiles().entries()) {
    if (status.status === 'available') continue;
    const player = getPlayer(slug);
    if (player) out.push({ player, status });
  }
  out.sort((a, b) => (b.status.last_updated ?? '').localeCompare(a.status.last_updated ?? ''));
  return out;
}

export function relTime(iso: string | undefined, now: Date = new Date()): string {
  if (!iso) return '';
  const t = new Date(iso);
  if (isNaN(t.getTime())) return '';
  const diffMs = now.getTime() - t.getTime();
  const m = Math.round(diffMs / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} hr ago`;
  const d = Math.round(h / 24);
  if (d < 30) return `${d} day${d === 1 ? '' : 's'} ago`;
  return t.toISOString().slice(0, 10);
}

const FLAG: Record<string, string> = {
  Argentina: '🇦🇷', Brazil: '🇧🇷', France: '🇫🇷', Germany: '🇩🇪', Spain: '🇪🇸',
  England: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', Portugal: '🇵🇹', Italy: '🇮🇹', Netherlands: '🇳🇱', Belgium: '🇧🇪',
  Mexico: '🇲🇽', 'United States': '🇺🇸', Canada: '🇨🇦', Croatia: '🇭🇷',
  'South Korea': '🇰🇷', Japan: '🇯🇵', Australia: '🇦🇺', 'Saudi Arabia': '🇸🇦',
  Iran: '🇮🇷', Morocco: '🇲🇦', Senegal: '🇸🇳', Ghana: '🇬🇭', Cameroon: '🇨🇲',
  Egypt: '🇪🇬', Tunisia: '🇹🇳', Nigeria: '🇳🇬', Algeria: '🇩🇿', 'Ivory Coast': '🇨🇮',
  'South Africa': '🇿🇦', Qatar: '🇶🇦', Uruguay: '🇺🇾', Ecuador: '🇪🇨', Peru: '🇵🇪',
  Colombia: '🇨🇴', Chile: '🇨🇱', Paraguay: '🇵🇾', Switzerland: '🇨🇭',
  Poland: '🇵🇱', Denmark: '🇩🇰', Serbia: '🇷🇸', Wales: '🏴󠁧󠁢󠁷󠁬󠁳󠁿', Scotland: '🏴󠁧󠁢󠁳󠁣󠁴󠁿',
  'Czech Republic': '🇨🇿', Austria: '🇦🇹', Turkey: '🇹🇷', Sweden: '🇸🇪',
  Norway: '🇳🇴', 'Bosnia and Herzegovina': '🇧🇦', Haiti: '🇭🇹', 'New Zealand': '🇳🇿',
  'Curaçao': '🇨🇼', 'Cape Verde': '🇨🇻', Iraq: '🇮🇶', Jordan: '🇯🇴', 'DR Congo': '🇨🇩',
  Uzbekistan: '🇺🇿', Panama: '🇵🇦',
};

export function flag(country: string): string {
  return FLAG[country] ?? '🏳️';
}

export const STATUS_LABEL: Record<StatusOverlay['status'], string> = {
  available: 'Available',
  yellow: 'One yellow',
  doubtful: 'Doubtful',
  injured: 'Injured',
  suspended: 'Suspended',
};

// ----- stage presentation -----
// Shared so the schedule, team pages, and home strip render knockout rounds
// with one consistent colour language.
export interface StageMeta {
  /** Compact label for chips/calendar: "R16", "QF", "Final". */
  short: string;
  /** Full label for headings. */
  label: string;
  /** Tailwind classes for a filled stage pill. */
  pill: string;
  /** Tailwind class for a stage accent dot / left border colour. */
  accent: string;
  /** Ordering rank, group stage = 0 → final highest. */
  rank: number;
}

const STAGE_META: Record<string, StageMeta> = {
  'Group stage': {
    short: 'Group', label: 'Group stage', rank: 0,
    pill: 'bg-ink-100 text-ink-600 dark:bg-ink-800 dark:text-ink-300',
    accent: 'bg-ink-300 dark:bg-ink-600',
  },
  'Round of 32': {
    short: 'R32', label: 'Round of 32', rank: 1,
    pill: 'bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300',
    accent: 'bg-sky-500',
  },
  'Round of 16': {
    short: 'R16', label: 'Round of 16', rank: 2,
    pill: 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300',
    accent: 'bg-blue-500',
  },
  'Quarter-final': {
    short: 'QF', label: 'Quarter-final', rank: 3,
    pill: 'bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300',
    accent: 'bg-violet-500',
  },
  'Semi-final': {
    short: 'SF', label: 'Semi-final', rank: 4,
    pill: 'bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-500/15 dark:text-fuchsia-300',
    accent: 'bg-fuchsia-500',
  },
  'Play-off for third place': {
    short: '3rd', label: 'Third-place play-off', rank: 5,
    pill: 'bg-teal-100 text-teal-700 dark:bg-teal-500/15 dark:text-teal-300',
    accent: 'bg-teal-500',
  },
  'Final': {
    short: 'Final', label: 'Final', rank: 6,
    pill: 'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200',
    accent: 'bg-amber-500',
  },
};

export function stageMeta(stage: string): StageMeta {
  return (
    STAGE_META[stage] ?? {
      short: stage, label: stage, rank: 9,
      pill: 'bg-ink-100 text-ink-600 dark:bg-ink-800 dark:text-ink-300',
      accent: 'bg-ink-300 dark:bg-ink-600',
    }
  );
}

/** Days between now and an ISO date, floored at 0. */
export function daysUntil(iso: string, now: Date = new Date()): number {
  const t = new Date(iso).getTime();
  return Math.max(0, Math.ceil((t - now.getTime()) / 86_400_000));
}

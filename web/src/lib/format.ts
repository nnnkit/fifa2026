// Presentation helpers shared by the schedule page, team pages, and the
// MatchRow component. Kickoff times are stored as host-local wall time tagged
// with a Z suffix, so we format `localDate` with timeZone UTC to print the
// literal local clock time; `dateUtc` formatted as UTC gives the true UTC time.

import type { ScheduleMatch, ScheduleTeam } from './data';

const hostTimeFmt = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'UTC', hour: '2-digit', minute: '2-digit', hour12: false,
});
const utcTimeFmt = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'UTC', hour: '2-digit', minute: '2-digit', hour12: false, timeZoneName: 'short',
});
const shortDateFmt = new Intl.DateTimeFormat('en-US', {
  timeZone: 'UTC', month: 'short', day: 'numeric',
});
const longDateFmt = new Intl.DateTimeFormat('en-US', {
  timeZone: 'UTC', weekday: 'long', month: 'long', day: 'numeric',
});
const weekdayFmt = new Intl.DateTimeFormat('en-US', { timeZone: 'UTC', weekday: 'short' });
const monthFmt = new Intl.DateTimeFormat('en-US', { timeZone: 'UTC', month: 'long', year: 'numeric' });

function hostInstant(m: ScheduleMatch): Date {
  return new Date(m.localDate ?? m.dateUtc);
}

export function hostTime(m: ScheduleMatch): string {
  return hostTimeFmt.format(hostInstant(m));
}
export function utcTime(m: ScheduleMatch): string {
  return utcTimeFmt.format(new Date(m.dateUtc));
}
export function hostDate(m: ScheduleMatch): string {
  return shortDateFmt.format(hostInstant(m));
}
export function hostWeekday(m: ScheduleMatch): string {
  return weekdayFmt.format(hostInstant(m));
}
export function longDateFromKey(key: string): string {
  return longDateFmt.format(new Date(`${key}T12:00:00Z`));
}
export function shortDateFromKey(key: string): string {
  return shortDateFmt.format(new Date(`${key}T12:00:00Z`));
}
export function weekdayFromKey(key: string): string {
  return weekdayFmt.format(new Date(`${key}T12:00:00Z`));
}
export function monthLabel(key: string): string {
  return monthFmt.format(new Date(`${key}-01T12:00:00Z`));
}

export function placeholderLabel(value: string | undefined): string {
  if (!value) return 'TBD';
  const winner = value.match(/^W(\d+)$/);
  if (winner) return `Winner match ${winner[1]}`;
  const runnerUp = value.match(/^RU(\d+)$/);
  if (runnerUp) return `Runner-up match ${runnerUp[1]}`;
  const groupWinner = value.match(/^1([A-L])$/);
  if (groupWinner) return `Winner Group ${groupWinner[1]}`;
  const groupRunnerUp = value.match(/^2([A-L])$/);
  if (groupRunnerUp) return `Runner-up Group ${groupRunnerUp[1]}`;
  const bestThird = value.match(/^3([A-L]+)$/);
  if (bestThird) return `Best 3rd ${bestThird[1].split('').join('/')}`;
  return value;
}

export function teamName(team: ScheduleTeam): string {
  return team.placeholder ? placeholderLabel(team.placeholder) : team.name;
}
export function teamSub(team: ScheduleTeam): string {
  return team.placeholder ? 'To be decided' : team.code;
}

/** Compact group label, "Group A" → "GRP A". */
export function groupShort(group?: string | null): string | null {
  if (!group) return null;
  const m = group.match(/Group\s+([A-L])/i);
  return m ? `GRP ${m[1]}` : group;
}

# -*- coding: utf-8 -*-
"""Build 04_LabSite/pulse.js from local development records.

Sources: git history of this repository, Claude Code session logs
(~/.claude/projects), Codex session logs (~/.codex/sessions), and the 3AI call
ledger (.agent_bus/history.jsonl). Only aggregates leave this script; no
session text, prompt or file content is written.
"""
import datetime as dt
import glob
import json
import os
import subprocess
import sys
import time
from collections import Counter

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(REPO, '04_LabSite', 'pulse.js')
HOME = os.path.expanduser('~')

# Commit scopes whose subject line may be shown publicly. Everything else is
# shown as a category label only.
PUBLIC_SCOPES = {
    'ladder': ('Ladder verification research', '래더 검증 연구'),
    'sci-paper': ('Paper status', '논문 진행'),
    'vision': ('Vision inspection', '비전 검사'),
    'line': ('Production line', '생산 라인'),
    'maia': ('MAIA', 'MAIA'),
    'paper': ('Paper', '논문'),
}
PRIVATE_SCOPES = {
    'govt': ('Grant preparation', '정부과제 준비'),
    'govt-rnd': ('Grant watch', '정부과제 정찰'),
}


def git(*args):
    return subprocess.run(['git', *args], cwd=REPO, capture_output=True,
                          text=True, encoding='utf-8').stdout.strip()


def commits():
    total = int(git('rev-list', '--count', 'HEAD') or 0)
    week = int(git('rev-list', '--count', '--since=7 days ago', 'HEAD') or 0)
    day = int(git('rev-list', '--count', '--since=24 hours ago', 'HEAD') or 0)
    days = Counter(git('log', '--since=14 days ago', '--format=%cs').split())
    today = dt.date.today()
    spark = [days.get((today - dt.timedelta(days=i)).isoformat(), 0)
             for i in range(13, -1, -1)]
    feed = []
    for line in git('log', '-20', '--format=%cI%x09%s').splitlines():
        ts, subject = line.split('\t', 1)
        scope = subject.split('(', 1)[1].split(')', 1)[0] if '(' in subject.split(':', 1)[0] else ''
        if scope in PUBLIC_SCOPES:
            label = PUBLIC_SCOPES[scope]
            text = subject.split(':', 1)[1].strip() if ':' in subject else subject
        elif scope in PRIVATE_SCOPES:
            label, text = PRIVATE_SCOPES[scope], ''
        else:
            label, text = ('Development', '개발'), ''
        feed.append({'t': ts, 'en': label[0], 'ko': label[1], 'text': text[:90]})
        if len(feed) == 8:
            break
    return {'total': total, 'week': week, 'day': day, 'spark14': spark,
            'last': git('log', '-1', '--format=%cI'), 'feed': feed}


def day_key(ts):
    return dt.datetime.fromtimestamp(ts).date().isoformat()


def claude_tokens(since, daily=None):
    seen, total = set(), 0
    for f in glob.glob(HOME + '/.claude/projects/**/*.jsonl', recursive=True):
        with open(f, encoding='utf-8', errors='ignore') as fh:
            for line in fh:
                if '"usage"' not in line:
                    continue
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                m = o.get('message') or {}
                u = m.get('usage')
                key = (m.get('id'), o.get('requestId'))
                if not u or key in seen:
                    continue
                seen.add(key)
                try:
                    t = dt.datetime.fromisoformat(o['timestamp'].replace('Z', '+00:00')).timestamp()
                except (KeyError, ValueError, AttributeError):
                    continue
                if t >= since:
                    n = sum(u.get(k) or 0 for k in ('input_tokens', 'output_tokens',
                            'cache_creation_input_tokens', 'cache_read_input_tokens'))
                    total += n
                    if daily is not None:
                        daily[day_key(t)] = daily.get(day_key(t), 0) + n
    return total


def codex_tokens(since, daily=None):
    total = 0
    for f in glob.glob(HOME + '/.codex/sessions/**/*.jsonl', recursive=True):
        if os.path.getmtime(f) < since:
            continue
        last = None
        with open(f, encoding='utf-8', errors='ignore') as fh:
            for line in fh:
                if 'total_token_usage' in line:
                    last = line
        if last:
            try:
                info = json.loads(last).get('payload', {}).get('info') or {}
                n = (info.get('total_token_usage') or {}).get('total_tokens') or 0
                total += n
                if daily is not None:
                    k = day_key(os.path.getmtime(f))
                    daily[k] = daily.get(k, 0) + n
            except ValueError:
                pass
    return total


def agent_calls():
    c = Counter()
    path = os.path.join(REPO, '.agent_bus', 'history.jsonl')
    with open(path, encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            try:
                c[json.loads(line).get('to') or '?'] += 1
            except ValueError:
                pass
    return {'codex': c['codex'], 'claude': c['opus5'], 'gemini': c['agy'],
            'total': c['codex'] + c['opus5'] + c['agy']}


def main():
    now = time.time()
    d30, d1 = now - 30 * 86400, now - 86400
    cl_daily, cx_daily = {}, {}
    cl30, cx30 = claude_tokens(d30, cl_daily), codex_tokens(d30, cx_daily)
    today = dt.date.today()
    days = [(today - dt.timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
    pulse = {
        'generated_at': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        'commits': commits(),
        'tokens': {'d30': cl30 + cx30, 'claude30': cl30, 'codex30': cx30,
                   'd1': claude_tokens(d1) + codex_tokens(d1),
                   'days14': days,
                   'claude14': [cl_daily.get(d, 0) for d in days],
                   'codex14': [cx_daily.get(d, 0) for d in days],
                   'note': 'Claude Code + Codex, cache reads included; Gemini not yet counted'},
        'agents': agent_calls(),
        'datasets': 3,
    }
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('window.PULSE = ' + json.dumps(pulse, ensure_ascii=False) + ';\n')
    print(json.dumps({k: pulse[k] for k in ('generated_at', 'tokens', 'agents')}, ensure_ascii=False))


if __name__ == '__main__':
    sys.exit(main())

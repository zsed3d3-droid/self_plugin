"""Scoped evidence retrieval. Stored text preserves wording after explicit secret redaction."""
import re
import hashlib
import json
import uuid


def evidence_excerpt(text, queries, limit=700):
    """Return one bounded, exact source substring near query matches."""
    total = len(text)
    start = 0
    if total > limit:
        needles = []
        for query in queries:
            for needle in [query.strip(), *re.findall(r'[\w가-힣]+', query)[:16]]:
                if needle and needle.casefold() not in {item.casefold() for item in needles}:
                    needles.append(needle)
        matches = []
        for needle in needles[:64]:
            for index, match in enumerate(re.finditer(re.escape(needle), text, re.IGNORECASE)):
                if index >= 8 or len(matches) >= 128:
                    break
                weight = 3 if len(re.findall(r'[\w가-힣]+', needle)) > 1 else 1
                matches.append((match.start(), match.end(), weight))
        starts = {0, *(min(total - limit, max(0, (a + b) // 2 - limit // 2)) for a, b, _ in matches)}
        # Stable earlier-source tie break; this selects a window, not a semantic answer.
        start = max(sorted(starts), key=lambda offset: sum(weight for a, b, weight in matches if offset <= a and b <= offset + limit))
    end = min(total, start + limit)
    return {'text': text[start:end], 'start': start, 'end': end,
            'total_chars': total, 'truncated': start > 0 or end < total}


def redact(text):
    patterns = [
        r'(?i)\b(?:sk|ghp|gho|github_pat)[-_][A-Za-z0-9_-]{12,}',
        r'(?im)(?:authorization\s*[:=]\s*bearer|api[_-]?key\s*[:=]|password\s*[:=]|secret\s*[:=]|access[_-]?token\s*[:=])\s*[^\s,;]+',
        r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b',
    ]
    for pattern in patterns:
        text = re.sub(pattern, '[REDACTED]', text)
    return text


def normalize(text, format):
    if format == 'text':
        return [{'role': 'user', 'text': text, 'line': 1, 'event_id': None}]
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        event = json.loads(line)
        if not isinstance(event, dict):
            raise ValueError('Each JSONL event must be an object')
        payload = event.get('payload', event)
        if not isinstance(payload, dict):
            raise ValueError('Invalid event payload')
        if event.get('type') == 'event_msg' and payload.get('type') == 'user_message':
            role, content = 'user', payload.get('message', '')
        else:
            if event.get('type') == 'response_item' and payload.get('type') != 'message':
                continue
            message = payload.get('message', {})
            if not isinstance(message, dict):
                message = {}
            role = payload.get('role') or message.get('role') or event.get('type')
            content = payload.get('content', message.get('content', ''))
        if role not in ('user', 'assistant'):
            continue
        if isinstance(content, list):
            content = '\n'.join(item.get('text', '') for item in content if isinstance(item, dict)
                                and item.get('type') in ('text', 'input_text', 'output_text'))
        if isinstance(content, str) and content.strip():
            rows.append({'role': role, 'text': content, 'line': number,
                         'event_id': event.get('uuid') or event.get('id') or payload.get('id')})
    return rows


def import_events(connection, text, source, format, project, topic='general', purpose='development'):
    rows = normalize(text, format)  # Parse before any inserts, so malformed input is atomic.
    added = 0
    ids = []
    for row in rows:
        clean = redact(row['text'])
        origin = str(row['event_id']) if row['event_id'] is not None else f'{source}:{row["line"]}'
        origin_key = hashlib.sha256(json.dumps([project, topic, purpose, origin, row['role']], ensure_ascii=False).encode()).hexdigest()
        digest = hashlib.sha256((origin_key + '\0' + clean).encode()).hexdigest()
        identifier = str(uuid.uuid4())
        result = connection.execute('''INSERT INTO evidence(id,digest,origin_key,project,topic,purpose,source,line,role,text)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(digest) DO NOTHING RETURNING id''',
            (identifier, digest, origin_key, project, topic, purpose, source, row['line'], row['role'], clean)).fetchone()
        if result:
            added += 1
            ids.append(result['id'])
    return {'added': added, 'parsed': len(rows), 'redacted': True, 'evidence_ids': ids}


def eligible(connection, project, topic=None, purpose=None):
    predicates = ['e.project=%s']
    params = [project]
    if topic is not None:
        predicates.append('e.topic=%s')
        params.append(topic)
    if purpose is not None:
        predicates.append('e.purpose=%s')
        params.append(purpose)
    # An exclusion is scoped to the evidence's project/topic/purpose. Corrections do not overwrite its original text.
    sql = '''SELECT e.id,e.digest,e.origin_key,e.project,e.topic,e.purpose,e.source,e.line,e.role,e.text,e.created,e.seq,
      assessment.rating feedback_rating,assessment.functionality,
      (SELECT f.correction FROM retrieval_feedback f WHERE f.evidence_id=e.id AND f.project=e.project
       AND f.topic=e.topic AND f.purpose=e.purpose AND f.kind='correct' ORDER BY f.seq DESC LIMIT 1) correction
      FROM evidence e LEFT JOIN feedback assessment ON e.source='feedback:' || assessment.id WHERE ''' + ' AND '.join(predicates) + ''' AND COALESCE(
      (SELECT f.kind FROM retrieval_feedback f WHERE f.evidence_id=e.id AND f.project=e.project
       AND f.topic=e.topic AND f.purpose=e.purpose ORDER BY f.seq DESC LIMIT 1),'') != 'suppress' '''
    return sql, params


def search(connection, query, project='personal', limit=8, topic=None, purpose=None):
    terms = re.findall(r'[\w가-힣]+', query)[:16]
    if not terms:
        return []
    base, params = eligible(connection, project, topic, purpose)
    matches = ['search_document @@ plainto_tsquery(\'simple\',%s)']
    match_params = [query]
    for term in terms:
        matches.append('text ILIKE %s ESCAPE \'\\\'')
        match_params.append('%' + term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%')
    sql = '''SELECT candidate.*,ts_rank_cd(to_tsvector('simple',candidate.text),plainto_tsquery('simple',%s)) rank
      FROM (''' + base + ''') candidate WHERE id IN (SELECT id FROM evidence WHERE ''' + ' OR '.join(matches) + ''')
      ORDER BY rank DESC,seq DESC LIMIT %s'''
    return [dict(row) for row in connection.execute(sql, [query, *params, *match_params, limit]).fetchall()]


def scope_inventory(connection, project, topic, purpose, limit=200):
    sql, params = eligible(connection, project, topic, purpose)
    total = connection.execute('SELECT count(*) total FROM (' + sql + ') scoped', params).fetchone()['total']
    rows = connection.execute(sql + ' ORDER BY e.seq DESC LIMIT %s', [*params, limit]).fetchall()
    return [dict(row) for row in rows], total

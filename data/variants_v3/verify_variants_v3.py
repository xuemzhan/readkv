#!/usr/bin/env python3
"""CPU-only verifier for the E1 variants_v3 data product.

No GPU, no model inference, no test scoring. Run:
    python3 data/variants_v3/verify_variants_v3.py
Exits non-zero on any inconsistency.
"""
import json, hashlib, collections, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V3 = os.path.join(ROOT, 'data', 'variants_v3')
A2 = os.path.join(ROOT, 'data', 'audit_2x2')
MANIFEST = os.path.join(V3, 'manifest.json')


def load(path):
    with open(path, 'r', encoding='utf-8', newline='') as f:
        return [json.loads(line) for line in f if line.strip()]


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha(path):
    return sha_bytes(open(path, 'rb').read())


def canon(rows):
    return ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows).encode('utf-8')


def text_key(r):
    return (r['context_A'], r['context_B'], r['query'], r.get('edited_span', ''))


def degenerate(r):
    return bool(r.get('must_flip')) and r['candidate_A'] == r['candidate_B']


def legacy(seed, split):
    return load(os.path.join(A2, 'legacy', f'{split}_seed{seed}.jsonl'))


def fixed(seed, split):
    return load(os.path.join(A2, 'fixed', f'{split}_seed{seed}.jsonl'))


def variant(v, seed, split):
    return load(os.path.join(V3, v, f'{split}_seed{seed}.jsonl'))


def check(cond, msg, failures):
    if not cond:
        failures.append(msg)


def main():
    m = json.load(open(MANIFEST, encoding='utf-8'))
    failures = []
    total = 0

    # 1. declared file inventory: hash / bytes / rows / families / slices / serialization
    for v, info in m['variants'].items():
        for fe in info['files']:
            total += 1
            path = os.path.join(ROOT, fe['path'])
            b = open(path, 'rb').read()
            rows = load(path)
            fams = collections.Counter(r['template_family'] for r in rows)
            slices = collections.Counter(r.get('slice_id', '?') for r in rows)
            check(sha_bytes(b) == fe['sha256'], f'{v}/{fe["path"]}: sha256', failures)
            check(len(b) == fe['bytes'], f'{v}/{fe["path"]}: bytes', failures)
            check(len(rows) == fe['rows'], f'{v}/{fe["path"]}: rows', failures)
            check(len(fams) == fe['template_family_count'], f'{v}/{fe["path"]}: family count', failures)
            check(set(fams) == set(fe['template_families']), f'{v}/{fe["path"]}: family set', failures)
            check(slices == collections.Counter(fe['slice_counts']), f'{v}/{fe["path"]}: slice counts', failures)
            check(sum(1 for r in rows if degenerate(r)) == fe['degenerate_mustflip_rows'],
                  f'{v}/{fe["path"]}: degenerate count', failures)
            check(b'\r' not in b and b.endswith(b'\n') and canon(rows) == b,
                  f'{v}/{fe["path"]}: canonical LF serialization', failures)

    # 2. rule recomputation against audit_2x2 sources
    for seed in (0, 1, 2):
        Ltr, Lva = legacy(seed, 'train'), legacy(seed, 'val')
        Ftr, Fva = fixed(seed, 'train'), fixed(seed, 'val')
        check(canon(variant('legacy_bundle', seed, 'train')) == canon(Ltr), f'legacy train s{seed}', failures)
        check(canon(variant('legacy_bundle', seed, 'val')) == canon(Lva), f'legacy val s{seed}', failures)
        check(canon(variant('fully_repaired', seed, 'train')) == canon(Ftr), f'fixed train s{seed}', failures)
        check(canon(variant('fully_repaired', seed, 'val')) == canon(Fva), f'fixed val s{seed}', failures)

        seen, expect = set(), []
        for r in Ltr:
            k = text_key(r)
            if k not in seen:
                seen.add(k)
                expect.append(r)
        check(canon(variant('dedup_only', seed, 'train')) == canon(expect), f'dedup train s{seed}', failures)
        check(canon(variant('dedup_only', seed, 'val')) == canon(Lva), f'dedup val s{seed}', failures)

        check(canon(variant('degenerate_only', seed, 'train')) == canon([r for r in Ltr if not degenerate(r)]),
              f'degenerate train s{seed}', failures)
        check(canon(variant('degenerate_only', seed, 'val')) == canon([r for r in Lva if not degenerate(r)]),
              f'degenerate val s{seed}', failures)

        etr, eva = variant('entity_disjoint_only', seed, 'train'), variant('entity_disjoint_only', seed, 'val')
        check(canon(etr) == canon(Ltr), f'entity train s{seed}', failures)
        for field in ('pair_id', 'template_family', 'correct_A', 'correct_B', 'must_flip',
                      'slice_id', 'token_count_A', 'token_count_B'):
            check([r[field] for r in eva] == [r[field] for r in Lva], f'entity val {field} s{seed}', failures)
        check(all(a['sample_id'] != b['sample_id'] for a, b in zip(eva, Lva)), f'entity sample_id s{seed}', failures)

        ttr, tva = variant('template_disjoint_only', seed, 'train'), variant('template_disjoint_only', seed, 'val')
        check(canon(ttr) == canon(Ltr), f'template train s{seed}', failures)
        for field in ('pair_id', 'template_family', 'context_A', 'context_B', 'candidate_A', 'candidate_B',
                      'correct_A', 'correct_B', 'edited_span', 'must_flip', 'token_count_A', 'token_count_B'):
            check([r[field] for r in tva] == [r[field] for r in Lva], f'template val {field} s{seed}', failures)
        check(all(a['query'] != b['query'] for a, b in zip(tva, Lva)), f'template query changed s{seed}', failures)

    if failures:
        print(f'FAIL ({len(failures)}):')
        for f in failures[:50]:
            print('  -', f)
        sys.exit(1)
    print(f'PASS: {total} files verified; all rule checks passed. CPU-only, no GPU, no test scoring.')


if __name__ == '__main__':
    main()

import json, time, statistics, httpx, os

URL = os.getenv("URL", "http://127.0.0.1:8080/analyze")

def token_count(s: str) -> int:
    return max(1, len(s.split()))

def quality_score(obj) -> float:
    # Proxy très simple: plus il y a d'items raisonnables, mieux c'est
    pts = 0
    if obj.get("summary"): pts += 1
    pts += min(2, len(obj.get("themes", [])))
    pts += min(2, len(obj.get("symbols", [])))
    pts += min(1, len(obj.get("advice", [])))
    return pts / 6.0  # score 0..1

latencies, scores = [], []
with open("eval/dataset.jsonl","r",encoding="utf-8") as f:
    for line in f:
        j = json.loads(line)
        t0 = time.time()
        r = httpx.post(URL, json=j, timeout=120)
        dt = (time.time()-t0)*1000
        latencies.append(dt)
        if r.status_code == 200:
            out = r.json()
            scores.append(quality_score(out))
            print(f"✓ {dt:.0f} ms  score≈{scores[-1]:.2f}  summary='{out.get('summary','')[:40]}…'")
        else:
            print(f"✗ {dt:.0f} ms  HTTP {r.status_code}: {r.text}")

print("\n== Résumé ==")
if scores:
    print(f"médiane latence: {statistics.median(latencies):.0f} ms")
    print(f"moyenne score: {statistics.mean(scores):.2f}")
    
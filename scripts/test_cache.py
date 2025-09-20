import time, requests
URL = "http://127.0.0.1:8080/analyze"
payload = {"text":"Je tombe dans un puits sans fin.","lang":"fr","use_rag":False}
def call():
    t0 = time.time()
    r = requests.post(URL, json=payload, timeout=120)
    ms = int((time.time()-t0)*1000)
    j = r.json()
    m = j.get("metrics", {})
    print(f"status={r.status_code} latency_ms={ms} cached_tokens={m.get('cached_tokens')} model={m.get('model')}")
    return j
print("1st call:"); call()
print("2nd call:"); call()

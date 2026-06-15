"""Exploratory QA probe — security, authorization/privacy, validation, abuse.
Run: python qa_probe.py   (uses an isolated test DB, scripted LLM)."""
import io
import os

os.environ["DERMAI_DATABASE_URL"] = "sqlite:///./qa_probe.db"
os.environ["DERMAI_AUTH_MODE"] = "prod"          # no dev-header bypass
os.environ["DERMAI_LLM_PROVIDER"] = "scripted"

import pathlib
from PIL import Image
from fastapi.testclient import TestClient

pathlib.Path("qa_probe.db").unlink(missing_ok=True)
from app.main import app

findings = []
def check(name, ok, severity="HIGH", detail=""):
    print(f"  [{'PASS' if ok else f'BUG[{severity}]'}] {name}" + (f" — {detail}" if not ok and detail else ""))
    if not ok:
        findings.append((severity, name, detail))

def img():
    b = io.BytesIO(); Image.new("RGB", (200, 200), (190, 120, 110)).save(b, "JPEG"); return b.getvalue()
def auth(t): return {"Authorization": "Bearer " + t}
def reg(c, u, role="patient", **x):
    return c.post("/auth/register", json={"username": u, "password": "pw", "role": role, **x})
def uid(c, t): return c.get("/auth/me", headers=auth(t)).json()["uid"]
def patient_with_session(c, u):
    t = reg(c, u, gender="Male", age=25).json()["token"]
    c.put("/profile/medical-history", headers=auth(t), json={"allergies": "none"})
    sid = c.post("/diagnose", headers=auth(t), files={"image": ("t.jpg", img(), "image/jpeg")}).json()["session_id"]
    return t, sid

with TestClient(app) as c:
    print("\n== A. Authentication & input validation ==")
    check("empty password rejected",
          c.post("/auth/register", json={"username": "v2", "password": ""}).status_code >= 400, "MED")
    check("whitespace-only username rejected",
          c.post("/auth/register", json={"username": "   ", "password": "pw"}).status_code >= 400,
          "MED", "username '   ' accepted as a real account")
    check("invalid role rejected",
          c.post("/auth/register", json={"username": "v3", "password": "pw", "role": "superuser"}).status_code == 400)
    reg(c, "alice")
    check("wrong password -> 401",
          c.post("/auth/login", json={"username": "alice", "password": "x"}).status_code == 401)
    tok = c.post("/auth/login", json={"username": "alice", "password": "pw"}).json()["token"]
    c.post("/auth/logout", headers=auth(tok))
    check("token rejected after logout",
          c.get("/auth/me", headers=auth(tok)).status_code == 401, "HIGH", "logged-out token still works")
    check("garbage token -> 401", c.get("/auth/me", headers=auth("garbage")).status_code == 401)
    check("no auth -> 401", c.get("/history").status_code == 401)

    print("\n== B. Authorization & privacy ==")
    ta, sa = patient_with_session(c, "pa")
    tb, sb = patient_with_session(c, "pb")
    a_uid = uid(c, ta)
    check("patient B cannot read patient A's report",
          c.get(f"/report/{sa}", headers=auth(tb)).status_code in (403, 404), "HIGH")
    check("patient B cannot answer A's chat",
          c.post("/chat/answer", headers=auth(tb), json={"session_id": sa, "answer": "x"}).status_code in (403, 404), "HIGH")
    check("patient blocked from /admin/stats", c.get("/admin/stats", headers=auth(ta)).status_code == 403)
    dt = reg(c, "doc1", role="doctor", specialization="derm").json()["token"]
    check("unverified doctor blocked from queue", c.get("/consult/queue", headers=auth(dt)).status_code == 403)
    at = c.post("/auth/login", json={"username": "admin", "password": "admin123"}).json()["token"]
    duid = c.get("/admin/pending", headers=auth(at)).json()["doctors"][0]["uid"]
    c.post("/admin/verify", headers=auth(at), json={"uid": duid, "approved": True})
    check("doctor cannot read UNRELATED patient's medical history",
          c.get(f"/profile/medical-history/{a_uid}", headers=auth(dt)).status_code in (403, 404), "HIGH",
          "any verified doctor can read ANY patient's full history (no consult link)")
    check("doctor cannot read UNRELATED patient's report",
          c.get(f"/report/{sa}", headers=auth(dt)).status_code in (403, 404), "HIGH",
          "any verified doctor can read ANY patient's report")

    print("\n== C. Diagnosis robustness ==")
    tc = reg(c, "pc", gender="Male", age=20).json()["token"]
    check("diagnose blocked before medical history",
          c.post("/diagnose", headers=auth(tc), files={"image": ("t.jpg", img(), "image/jpeg")}).status_code == 428)
    c.put("/profile/medical-history", headers=auth(tc), json={"allergies": "none"})
    check("non-image upload rejected",
          c.post("/diagnose", headers=auth(tc), files={"image": ("t.txt", b"not an image", "text/plain")}).status_code == 400)

    print("\n== D. Admin / consult edge cases ==")
    check("admin cannot verify a patient",
          c.post("/admin/verify", headers=auth(at), json={"uid": a_uid, "approved": True}).status_code == 404)
    check("admin cannot delete own account",
          c.delete(f"/admin/users/{uid(c, at)}", headers=auth(at)).status_code == 400)
    check("accept non-existent consult -> 404",
          c.post("/consult/nope/accept", headers=auth(dt)).status_code == 404)
    check("negative age rejected in medical history",
          c.put("/profile/medical-history", headers=auth(tc), json={"age": -5}).status_code >= 400,
          "LOW", "negative age stored without validation")

print("\n==================== QA SUMMARY ====================")
for sev in ("HIGH", "MED", "LOW"):
    for s, n, d in [f for f in findings if f[0] == sev]:
        print(f"  {s}: {n}" + (f" — {d}" if d else ""))
print(f"\nTotal findings: {len(findings)}")
try:
    pathlib.Path("qa_probe.db").unlink(missing_ok=True)
except OSError:
    pass   # Windows holds the file handle until the process exits; harmless

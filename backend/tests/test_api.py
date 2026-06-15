"""End-to-end API tests covering auth, RBAC, the medical-history gate, diagnosis,
cross-questioning, consultation, admin, reports, and Google config."""
import io

from PIL import Image


def img_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (256, 256), (190, 120, 110)).save(buf, "JPEG")
    return buf.getvalue()


def auth(token):
    return {"Authorization": "Bearer " + token}


def reg(client, username, role="patient", **extra):
    r = client.post("/auth/register",
                    json={"username": username, "password": "pw", "role": role, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def diagnosed_patient(client, username):
    """Register a patient, complete medical history, run one diagnosis."""
    token = reg(client, username, gender="Male", age=25)["token"]
    client.put("/profile/medical-history", headers=auth(token), json={"allergies": "none", "smoking": "never"})
    r = client.post("/diagnose", headers=auth(token),
                    files={"image": ("t.jpg", img_bytes(), "image/jpeg")},
                    data={"body_region": "arm"})
    assert r.status_code == 200, r.text
    return token, r.json()


# ---------------- tests ----------------

def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_register_login_duplicate(client):
    d = reg(client, "alice", gender="Female", age=30)
    assert d["user"]["role"] == "patient"
    assert client.post("/auth/register", json={"username": "alice", "password": "x"}).status_code == 409
    assert client.post("/auth/login", json={"username": "alice", "password": "pw"}).status_code == 200
    assert client.post("/auth/login", json={"username": "alice", "password": "nope"}).status_code == 401


def test_rbac_patient_blocked_from_admin(client):
    token = reg(client, "bob")["token"]
    assert client.get("/admin/stats", headers=auth(token)).status_code == 403


def test_medical_history_gate(client):
    token = reg(client, "carol", gender="Male", age=22)["token"]
    # blocked before history
    r = client.post("/diagnose", headers=auth(token),
                    files={"image": ("t.jpg", img_bytes(), "image/jpeg")})
    assert r.status_code == 428
    # complete it
    r = client.put("/profile/medical-history", headers=auth(token),
                   json={"allergies": "pollen", "chronic_conditions": "asthma"})
    assert r.status_code == 200 and r.json()["completed"] is True
    # now allowed
    r = client.post("/diagnose", headers=auth(token),
                    files={"image": ("t.jpg", img_bytes(), "image/jpeg")})
    assert r.status_code == 200, r.text
    brief = r.json()["brief"]
    assert brief["disease"] and brief["medical_history"]["chronic_conditions"] == "asthma"
    assert brief["insights"] and brief["insights"]["summary"]


def test_chat_and_result(client):
    token, d = diagnosed_patient(client, "dan")
    sid = d["session_id"]
    awaiting, done = d["awaiting_answer"], not d["awaiting_answer"]
    seen = set()
    for _ in range(6):
        if done:
            break
        turn = client.post("/chat/answer", headers=auth(token),
                           json={"session_id": sid, "answer": "two weeks, itchy at night"})
        assert turn.status_code == 200
        msg = turn.json()["message"]
        assert msg not in seen, "question repeated!"   # dedup check
        seen.add(msg)
        done = turn.json()["done"]
    if done:
        assert client.get(f"/chat/{sid}/result", headers=auth(token)).status_code == 200


def verified_dermatologist(client, username="drsmith", spec="Dermatology"):
    """Register a doctor, have the seeded admin verify them, return (token, uid)."""
    doc = reg(client, username, role="doctor", specialization=spec)
    at = client.post("/auth/login", json={"username": "admin", "password": "admin123"}).json()["token"]
    client.post("/admin/verify", headers=auth(at), json={"uid": doc["user"]["uid"], "approved": True})
    return doc["token"], doc["user"]["uid"]


def test_appointment_flow_and_doctor_context(client):
    token, d = diagnosed_patient(client, "erin")
    sid = d["session_id"]
    dtoken, duid = verified_dermatologist(client)

    # doctor publishes an availability slot
    slots = client.post("/consult/availability", headers=auth(dtoken),
                        json={"slots": ["2026-06-20T17:00:00"]})
    assert slots.status_code == 200 and slots.json()
    slot_id = slots.json()[0]["id"]

    # patient sees the dermatologist + open slot, then books it
    docs = client.get("/consult/doctors", headers=auth(token)).json()
    chosen = next(x for x in docs if x["uid"] == duid)
    assert any(s["id"] == slot_id for s in chosen["slots"])
    case = client.post("/consult/request", headers=auth(token),
                       json={"session_id": sid, "doctor_id": duid, "slot_id": slot_id,
                             "note": "please review"}).json()
    assert case["room"] and case["mode"] == "video" and case["status"] == "pending"

    # double-booking the same slot is rejected
    assert client.post("/consult/request", headers=auth(token),
                       json={"session_id": sid, "doctor_id": duid, "slot_id": slot_id}).status_code == 409

    # the doctor sees the request WITH full context (history + report + brief)
    assert any(c["id"] == case["id"] for c in client.get("/consult/requests", headers=auth(dtoken)).json())
    detail = client.get(f"/consult/{case['id']}", headers=auth(dtoken))
    assert detail.status_code == 200
    dj = detail.json()
    assert dj["medical_history"] and dj["report_url"].endswith(sid) and dj["brief"]["disease"]

    # the doctor can see the affected-area photo (scoped by the consult relationship)
    photo = client.get(f"/image/{sid}?token={dtoken}")
    assert photo.status_code == 200 and photo.headers["content-type"] == "image/jpeg"

    # confirm -> patient is notified
    assert client.post(f"/consult/{case['id']}/confirm", headers=auth(dtoken)).json()["status"] == "confirmed"
    notes = client.get("/notifications", headers=auth(token)).json()
    assert any(n["kind"] == "appointment" and not n["read"] for n in notes)
    assert client.get("/notifications/unread_count", headers=auth(token)).json()["unread"] >= 1

    # now (relationship exists) the doctor may read the patient's history
    assert client.get(f"/profile/medical-history/{duid and case['patient_id']}",
                      headers=auth(dtoken)).status_code == 200


def test_non_dermatologist_cannot_consult(client):
    """DermAI: a verified non-dermatologist is barred from online consults."""
    token, _ = diagnosed_patient(client, "harry")
    dtoken, duid = verified_dermatologist(client, "drcardio", spec="Cardiology")
    # cannot publish availability
    assert client.post("/consult/availability", headers=auth(dtoken),
                       json={"slots": ["2026-06-21T10:00:00"]}).status_code == 403
    # does not appear in the patient's dermatologist list
    assert all(x["uid"] != duid for x in client.get("/consult/doctors", headers=auth(token)).json())


def test_admin_patient_registry(client):
    token, d = diagnosed_patient(client, "ivy")
    at = client.post("/auth/login", json={"username": "admin", "password": "admin123"}).json()["token"]
    # list + search by username
    listed = client.get("/admin/patients?q=ivy", headers=auth(at))
    assert listed.status_code == 200
    row = next(p for p in listed.json() if p["username"] == "ivy")
    # detail shows the screening and its disease
    detail = client.get(f"/admin/patients/{row['uid']}", headers=auth(at)).json()
    assert detail["screenings"] and detail["screenings"][0]["disease"]
    assert detail["medical_history"]


def test_admin_flow(client):
    at = client.post("/auth/login", json={"username": "admin", "password": "admin123"}).json()["token"]
    stats = client.get("/admin/stats", headers=auth(at))
    assert stats.status_code == 200 and "patients" in stats.json()
    reg(client, "drv", role="doctor")
    docs = client.get("/admin/doctors", headers=auth(at)).json()
    uid = next(d["uid"] for d in docs if d["username"] == "drv")
    r = client.post("/admin/doctors/verify", headers=auth(at), json={"uid": uid, "approved": True})
    assert r.status_code == 200 and r.json()["verified"] is True


def test_report_pdf(client):
    token, d = diagnosed_patient(client, "fred")
    r = client.get(f"/report/{d['session_id']}", headers=auth(token))
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


def test_report_token_query(client):
    token, d = diagnosed_patient(client, "gina")
    # report openable via ?token= (used by the app links)
    r = client.get(f"/report/{d['session_id']}?token={token}")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"


def test_google_config(client):
    r = client.get("/auth/google-config")
    assert r.status_code == 200 and "client_id" in r.json()


def test_admin_reject_deletes_account(client):
    at = client.post("/auth/login", json={"username": "admin", "password": "admin123"}).json()["token"]
    uid = reg(client, "rejectme", role="doctor")["user"]["uid"]
    pend = client.get("/admin/pending", headers=auth(at)).json()
    assert any(d["uid"] == uid for d in pend["doctors"])
    assert client.delete(f"/admin/users/{uid}", headers=auth(at)).status_code == 200
    pend2 = client.get("/admin/pending", headers=auth(at)).json()
    assert not any(d["uid"] == uid for d in pend2["doctors"])

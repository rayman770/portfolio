import os, time, hmac, bcrypt
from pathlib import Path
from PIL import Image
import streamlit as st

# ---------- Config ----------
st.set_page_config(page_title="Architecture Case Studies", page_icon="🧭", layout="wide")
ASSETS = Path("assets")

# Access control: set ONE of these in Streamlit Cloud (Settings → Secrets)
#   ACCESS_CODE          = "jjeongarch"                 # plaintext (simple)
#   ACCESS_CODE_HASH     = bcrypt hash of your code     # stronger
ACCESS_CODE_HASH = os.getenv("ACCESS_CODE_HASH", "") or st.secrets.get("ACCESS_CODE_HASH", "")
ACCESS_CODE      = os.getenv("ACCESS_CODE", "")      or st.secrets.get("ACCESS_CODE", "")

# ---------- Auth helpers ----------
def is_authed():
    if st.session_state.get("authed"):
        return True
    qp = st.experimental_get_query_params()
    if "code" in qp and qp["code"]:
        return verify_code(qp["code"][0])
    return False

def verify_code(code: str) -> bool:
    if ACCESS_CODE_HASH:
        try:
            ok = bcrypt.checkpw(code.encode(), ACCESS_CODE_HASH.encode())
        except Exception:
            ok = False
        st.session_state["authed"] = bool(ok)
        return ok
    if ACCESS_CODE:
        ok = hmac.compare_digest(code, ACCESS_CODE)
        st.session_state["authed"] = bool(ok)
        return ok
    st.error("No access code configured. Set ACCESS_CODE or ACCESS_CODE_HASH.")
    st.session_state["authed"] = False
    return False

# ---------- Small helpers ----------
def kpi(label, value, sub=""):
    c = st.container(border=True)
    c.metric(label, value, sub)

def load_first(*names: str) -> Image.Image | None:
    """Return the first image that exists under assets/, or None."""
    for n in names:
        p = ASSETS / n
        if p.exists():
            try:
                return Image.open(p)
            except Exception:
                pass
    return None

# ---------- Sidebar gate ----------
with st.sidebar:
    st.header("🔒 Access")
    st.caption("**Hint:** the access code is printed at the **top-right of my resume**.")
    if not is_authed():
        pin = st.text_input("Enter access code", type="password")
        if st.button("Unlock"):
            if verify_code(pin):
                st.success("Welcome!")
                time.sleep(0.6)
                st.rerun()
            else:
                st.error("Wrong code")
        st.stop()
    st.success("Access granted")

# ---------- Header ----------
st.title("Architecture Case Studies")
st.caption("Interactive snapshots of recent infrastructure transformations.")

# ============================================================
# Case 1 — FE containerized + AKS with B/E (BFF)
# ============================================================
st.subheader("1) FE containerized + AKS with B/E (BFF pattern)")

img_fe = load_first(
    "FE_Arch_Improvement.webp",
    "fe.webp", "fe-after.webp"  # optional alternates
)
col1, col2 = st.columns([1.2, 0.8])
with col1:
    if img_fe:
        st.image(img_fe, use_column_width=True)
    else:
        st.warning("FE image not found in assets/")
with col2:
    st.markdown("""
- Frontend moved from **Storage static hosting** → **AKS pods**  
- **Single origin** → CORS removed, lower latency  
- Private Link from AFD → AKS; FE↔BE in-cluster (BFF)  
- Cleaner deploys/rollback/observability
""")
    k1,k2,k3=st.columns(3)
    with k1: kpi("Latency", "↓", "fewer edge hops")
    with k2: kpi("CORS", "eliminated")
    with k3: kpi("Security", "↑", "no public API")

st.divider()

# ============================================================
# Case 2 — Docker Hub proxy cache (Nexus)
# ============================================================
st.subheader("2) Eliminated external dependency w/ Nexus Docker proxy cache")

img_proxy = load_first(
    "Nexus_Improvement.webp",
    "proxy.webp", "proxy-after.webp"
)
col1, col2 = st.columns([1.2, 0.8])
with col1:
    if img_proxy:
        st.image(img_proxy, use_column_width=True)
    else:
        st.warning("Nexus/Proxy image not found in assets/")
with col2:
    st.markdown("""
- Configured **Nexus Docker proxy** in-cluster (pull-through cache)  
- GitOps: manifests now pull from `docker-group.dev.sgarch.net`  
- **Reliability:** AKS upgrades no longer hit Docker Hub rate limits  
- **Performance:** cold pulls served from cache
""")
    k1,k2=st.columns(2)
    with k1: kpi("429 errors", "0", "during upgrades")
    with k2: kpi("Pull time", "~60 ms", "cached layer")

st.divider()

# ============================================================
# Case 3 — Keycloak clustering + build cache
# ============================================================
st.subheader("3) Keycloak: StatefulSet clustering + build cache (PVC)")

img_kc = load_first(
    "Kecloak After.webp",           # your current file name (with space + typo)
    "Keycloak_Improvement.webp",    # nicer alternative if you rename later
    "kc.webp", "kc-after.webp"
)
col1, col2 = st.columns([1.2, 0.8])
with col1:
    if img_kc:
        st.image(img_kc, use_column_width=True)
    else:
        st.warning("Keycloak image not found in assets/")
with col2:
    st.markdown("""
- **StatefulSet** + **Headless Service**; **DNS_PING** + **JGroups/Infinispan** replicate sessions  
- **InitContainer build-cache**: cache Quarkus build to PVC, `--optimized` start  
- **Startup:** ~6 min → **~55 s**  
- No sticky required; **any pod** can complete OAuth flow
""")
    k1,k2,k3=st.columns(3)
    with k1: kpi("Startup", "~55 s", "from 6+ min")
    with k2: kpi("HA", "Multi-pod", "podAntiAffinity + PDB")
    with k3: kpi("Auth errors", "0", "during rollout")

st.divider()
st.write("📄 Download the static PDF version:  ", "[resume.pdf](resume.pdf)")

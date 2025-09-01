import os, time, bcrypt
from pathlib import Path
from PIL import Image
import streamlit as st
from streamlit_image_comparison import image_comparison

# ---------- Config ----------
st.set_page_config(page_title="Architecture Case Studies", page_icon="🧭", layout="wide")
ASSETS = Path("assets")

# Use a bcrypt hash in your environment: ACCESS_CODE_HASH
# Generate one locally: 
#   python - <<'PY'
#   import bcrypt; print(bcrypt.hashpw(b"your-pin", bcrypt.gensalt()).decode())
#   PY
ACCESS_CODE_HASH = os.getenv("ACCESS_CODE_HASH", "")

# ---------- Tiny Gate ----------
def is_authed():
    if st.session_state.get("authed"):
        return True
    # also accept ?code= query param
    qp = st.experimental_get_query_params()
    if "code" in qp and qp["code"]:
        return verify_code(qp["code"][0])
    return False

def verify_code(code: str) -> bool:
    if not ACCESS_CODE_HASH:
        return True  # if you forgot to set the hash, don't block access
    try:
        ok = bcrypt.checkpw(code.encode(), ACCESS_CODE_HASH.encode())
    except Exception:
        ok = False
    st.session_state["authed"] = bool(ok)
    return ok

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
    st.write("Tip: share a one-line hint in your resume (e.g., last 4 digits of …)")

# ---------- Header ----------
st.title("Architecture Case Studies")
st.caption("Interactive before/after views of recent infrastructure transformations.")

def kpi(label, value, sub=""):
    c = st.container(border=True)
    c.metric(label, value, sub)

# ---------- Case 1: FE containerized + AKS with BE (BFF) ----------
st.subheader("1) FE containerized + AKS with B/E (BFF pattern)")
col1, col2 = st.columns([1.2, 0.8])
with col1:
    image_comparison(
        img1=Image.open(ASSETS/"fe-before.webp"),
        img2=Image.open(ASSETS/"fe-after.webp"),
        label1="Before", label2="After", width=900,
    )
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

# ---------- Case 2: Docker Hub proxy cache (Nexus) ----------
st.subheader("2) Eliminated external dependency w/ Nexus Docker proxy cache")
col1, col2 = st.columns([1.2, 0.8])
with col1:
    image_comparison(
        img1=Image.open(ASSETS/"proxy-before.webp"),
        img2=Image.open(ASSETS/"proxy-after.webp"),
        label1="Before (429s via Hub)", label2="After (cached via Nexus)", width=900,
    )
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

# ---------- Case 3: Keycloak clustering + build cache ----------
st.subheader("3) Keycloak: StatefulSet clustering + build cache (PVC)")
col1, col2 = st.columns([1.2, 0.8])
with col1:
    image_comparison(
        img1=Image.open(ASSETS/"kc-before.webp"),
        img2=Image.open(ASSETS/"kc-after.webp"),
        label1="Before (sticky, no replication)", label2="After (DNS_PING + Infinispan)", width=900,
    )
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

import os, time, hmac, bcrypt
from pathlib import Path
from PIL import Image
import streamlit as st

# ---------- Config ----------
st.set_page_config(page_title="Architecture Improvement", page_icon="🧭", layout="wide")
ASSETS = Path("assets")

# Access control (set ONE of these under Settings → Secrets)
ACCESS_CODE_HASH = os.getenv("ACCESS_CODE_HASH", "") or st.secrets.get("ACCESS_CODE_HASH", "")
ACCESS_CODE      = os.getenv("ACCESS_CODE", "")      or st.secrets.get("ACCESS_CODE", "")

# ---------- Auth ----------
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

# ---------- Helpers ----------
def kpi(label, value, sub=""):
    c = st.container(border=True)
    c.metric(label, value, sub)

def load_first(*names: str):
    for n in names:
        p = ASSETS / n
        if p.exists():
            try:
                return Image.open(p)
            except Exception:
                pass
    return None

def bullet_box(title: str, bullets: list[str]):
    c = st.container(border=True)
    c.markdown(f"**{title}**")
    for b in bullets:
        c.markdown(f"- {b}")
    return c

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
st.title("Architecture Improvement")
st.caption("Three recent infrastructure transformations with measurable impact.")

# ============================================================
# Case 1 — FE Storage SPA → FE on AKS (BFF)
# ============================================================
st.subheader("1) **F/E Storage Account + B/E on AKS (SPA)** → **F/E containerized on AKS with B/E (BFF)**")

img_fe = load_first("FE_Arch_Improvement.webp", "fe.webp")
col1, col2 = st.columns([1.2, 0.8])
with col1:
    if img_fe: st.image(img_fe, use_column_width=True)
    else:      st.warning("FE image not found in assets/")

with col2:
    bullet_box("Before (SPA + public API)", [
        "Frontend hosted on Storage static website",
        "Browser calls **public API** through the edge → CORS & more hops",
        "Azure Front Door routes to Storage (FE) and AKS (API) separately",
    ])
    bullet_box("After (BFF on AKS)", [
        "FE containerized & deployed **with B/E** in the same AKS cluster",
        "**Single origin** via AFD → AKS over Private Link (no CORS)",
        "FE ↔ BE are **in-cluster** service-to-service (BFF pattern)",
        "Simpler deploys/rollback/observability",
    ])
    k1, k2 = st.columns(2)
    with k1: kpi("Latency", "↓", "fewer edge hops")
    with k2: kpi("Security", "↑", "no public API")

# ---- Traffic Flow ----
st.markdown("#### Traffic Flow (Before vs. After)")
flow = st.container(border=True)
flow.markdown("""
1) **Client → Azure FD**  
   - Browser → Azure FD with WAF over HTTPS; TLS terminates at AFD  
   - **Before:** Two hosts (F/E & B/E) ⇒ CORS required  
   - **After:** One host ⇒ no CORS for web ↔ API  

2) **Azure FD → Origin via Private Link**  
   - AFD → **Private Endpoint (consumer)** → **Private Link Service (provider)** performs **SNAT** to the origin  
   - **Before (F/E origin):** PLS → **Storage static website** (HTML/JS/CSS); SPA embeds API base URL  
   - **After (AKS origin):** PLS → **Internal Standard LB** → **Nginx Ingress (AKS)**  

3) **App ↔ API Call Path (Main Change)**  
   - **Before (SPA + public API):** Browser JS calls API directly via AFD to AKS  
   - **After (BFF):** Next.js server (FE pods) calls BE **in-cluster** via ClusterIP/Service DNS  
     `http://be-svc.<ns>.svc.cluster.local`  

4) **AKS workload egress via Firewall**  
   - AKS subnet UDR → **Azure Firewall**; Firewall performs **SNAT** to its Public IP for internet access  

5) **DNS Proxy (centralized resolution)**  
   - Firewall forwards to **Azure DNS / Private Resolver** so Private Link names resolve correctly
""")

# ---- Transformation Highlights ----
st.markdown("#### Transformation Highlights")
hi = st.container(border=True)
hi.markdown("""
**1) Performance & Cost**  
- In-cluster FE→BE calls (BFF) cut cross-Internet/edge hops ⇒ **lower latency**  
- **Egress savings:** FE↔BE traffic stays inside the cluster, not over the public edge  

**2) Security**  
- Public API removed: API endpoint is **ClusterIP-only**; origin reachable only via  
  **AFD → PE (consumer) → PLS (provider) → Internal Standard LB → Nginx Ingress (AKS)**  
- Edge secured with **AFD WAF** + **Private Link** to origin  
- Single controlled egress: all AKS outbound flows **SNAT** through Azure Firewall ⇒ easy allow-listing & audit  

**3) DevOps & Observability**  
- Containerized FE with BE on AKS ⇒ unified **CI/CD**, version control & fast rollback  
- Cleaner telemetry: unified **health probes & logging**
""")

st.divider()

# ============================================================
# Case 2 — Direct Docker Hub → Nexus proxy cache
# ============================================================
st.subheader("2) **Direct pulls from Docker Hub** → **In-cluster Nexus Docker proxy (pull-through cache)**")

img_proxy = load_first("Nexus_Improvement.webp", "proxy.webp")
col1, col2 = st.columns([1.2, 0.8])
with col1:
    if img_proxy: st.image(img_proxy, use_column_width=True)
    else:         st.warning("Nexus/Proxy image not found in assets/")

with col2:
    bullet_box("Before (external dependency)", [
        "Every node/pod pulled images from **Docker Hub** via Firewall SNAT",
        "Hit **429 rate-limits** during AKS upgrades",
        "Slow cold pulls; no in-cluster cache",
    ])
    bullet_box("After (internal proxy cache)", [
        "**Nexus Docker proxy** inside AKS (pull-through cache via Ingress)",
        "Manifests retargeted to `docker-group.dev.sgarch.net` (GitOps)",
        "Only **cache-miss** goes to Docker Hub; reliable upgrades",
        "Private registry endpoint improves control & auditability",
    ])
    k1,k2=st.columns(2)
    with k1: kpi("429 errors", "0", "AKS upgrades")
    with k2: kpi("Cold pull", "~60 ms", "cached layer")

st.divider()

# ============================================================
# Case 3 — Keycloak Deployment → StatefulSet clustering + build cache
# ============================================================
st.subheader("3) **Keycloak Deployment + sticky sessions** → **StatefulSet clustering + build cache (PVC)**")

img_kc = load_first("Kecloak After.webp", "Keycloak_Improvement.webp", "kc.webp")
col1, col2 = st.columns([1.2, 0.8])
with col1:
    if img_kc: st.image(img_kc, use_column_width=True)
    else:      st.warning("Keycloak image not found in assets/")

with col2:
    bullet_box("Before (no clustering)", [
        "Ran as a Deployment; tried sticky sessions at ingress",
        "Quarkus build on each start → **~6 min cold start**",
        "Multi-pod token exchange intermittently failed (no shared cache)",
    ])
    bullet_box("After (HA + fast start)", [
        "Migrated to **StatefulSet** + **Headless Service**",
        "**DNS_PING + JGroups/Infinispan** replicate auth/session state",
        "InitContainer caches Quarkus build to **PVC**; Keycloak `--optimized` start",
        "**Startup ~55 s**; any pod can complete OAuth flow",
    ])
    k1,k2,k3=st.columns(3)
    with k1: kpi("Startup", "~55 s", "from 6+ min")
    with k2: kpi("HA", "Multi-pod", "podAntiAffinity + PDB")
    with k3: kpi("Auth errors", "0", "during rollout")

st.divider()
st.write("📄 Download the static PDF version:  ", "[resume.pdf](resume.pdf)")

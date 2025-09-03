import os, time, hmac, bcrypt
from pathlib import Path
from PIL import Image
import streamlit as st
from streamlit.components.v1 import html as html_component

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

def load_img(path: Path):
    try:
        return Image.open(path)
    except Exception:
        return None

def bullet_box(title: str, bullets: list[str]):
    c = st.container(border=True)
    c.markdown(f"**{title}**")
    for b in bullets:
        c.markdown(f"- {b}")
    return c

def show_drawio_html(filename: str, height: int = 740, scrolling: bool = False) -> bool:
    """
    Embed a draw.io HTML export from assets/. Returns True if rendered, else False.
    Export from draw.io with: File → Export as → HTML ✓ Include a copy of my diagram.
    """
    p = ASSETS / filename
    if not p.exists():
        st.warning(f"Missing: assets/{filename}")
        return False
    try:
        html_str = p.read_text(encoding="utf-8", errors="ignore")
        html_component(html_str, height=height, scrolling=scrolling)
        return True
    except Exception as e:
        st.error(f"Could not embed {filename}: {e}")
        return False

def show_before_after(prefix: str, before_title: str, before_bullets: list[str],
                      after_title: str, after_bullets: list[str], height: int = 740):
    """
    Render two tabs (Before / After). Each tab shows:
      - LEFT: draw.io HTML export (prefix_before.html / prefix_after.html), fallback to webp
      - RIGHT: a summarized bullet box (Before/After)
    """
    tabs = st.tabs(["Before", "After"])

    # Before tab
    with tabs[0]:
        colL, colR = st.columns([1.2, 0.8])
        with colL:
            if not show_drawio_html(f"{prefix}_before.html", height=height):
                img = load_img(ASSETS / f"{prefix}_before.webp")
                if img: st.image(img, use_column_width=True)
                else:   st.warning(f"Also tried fallback: {prefix}_before.webp")
        with colR:
            bullet_box(before_title, before_bullets)

    # After tab
    with tabs[1]:
        colL, colR = st.columns([1.2, 0.8])
        with colL:
            if not show_drawio_html(f"{prefix}_after.html", height=height):
                img = load_img(ASSETS / f"{prefix}_after.webp")
                if img: st.image(img, use_column_width=True)
                else:   st.warning(f"Also tried fallback: {prefix}_after.webp")
        with colR:
            bullet_box(after_title, after_bullets)

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
    # Optional: quick inspector to debug paths
    # if st.toggle("🛠 Assets inspector", value=False):
    #     st.write(sorted(p.name for p in ASSETS.iterdir() if p.is_file()))

# ---------- Header ----------
st.title("Architecture Improvement")
st.caption("Three recent infrastructure transformations with measurable impact.")

# ============================================================
# Case 1 — FE Storage SPA → FE on AKS (BFF)
# ============================================================
st.subheader("1) **F/E Storage Account + B/E on AKS (SPA)** → **F/E containerized on AKS with B/E (BFF)**")

show_before_after(
    prefix="fe",
    before_title="Before (SPA + public API)",
    before_bullets=[
        "Frontend hosted on Storage static website",
        "Browser calls **public API** through the edge → CORS & more hops",
        "Azure Front Door routes to Storage (FE) and AKS (API) separately",
    ],
    after_title="After (BFF on AKS)",
    after_bullets=[
        "FE containerized & deployed **with B/E** in the same AKS cluster",
        "**Single origin** via AFD → AKS over Private Link (no CORS)",
        "FE ↔ BE are **in-cluster** service-to-service (BFF pattern)",
        "Simpler deploys/rollback/observability",
    ],
    height=740,
)

# KPIs under the tabs (summarizing the improvement)
k1, k2 = st.columns(2)
with k1: kpi("Latency", "↓", "fewer edge hops")
with k2: kpi("Security", "↑", "no public API")

# ---- Traffic Flow (comprehensive) ----
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

show_before_after(
    prefix="nexus",
    before_title="Before (external dependency)",
    before_bullets=[
        "Every node/pod pulled images from **Docker Hub** via Firewall SNAT",
        "Hit **429 rate-limits** during AKS upgrades",
        "Slow cold pulls; no in-cluster cache",
    ],
    after_title="After (internal proxy cache)",
    after_bullets=[
        "**Nexus Docker proxy** inside AKS (pull-through cache via Ingress)",
        "Manifests retargeted to `docker-group.dev.sgarch.net` (GitOps)",
        "Only **cache-miss** goes to Docker Hub; reliable upgrades",
        "Private registry endpoint improves control & auditability",
    ],
    height=740,
)

st.divider()

# ============================================================
# Case 3 — Keycloak Deployment → StatefulSet clustering + build cache
# ============================================================
st.subheader("3) **Keycloak Deployment + sticky sessions** → **StatefulSet clustering + build cache (PVC)**")

show_before_after(
    prefix="keycloak",
    before_title="Before (no clustering)",
    before_bullets=[
        "Ran as a Deployment; tried sticky sessions at ingress",
        "Quarkus build on each start → **~6 min cold start**",
        "Multi-pod token exchange intermittently failed (no shared cache)",
    ],
    after_title="After (HA + fast start)",
    after_bullets=[
        "Migrated to **StatefulSet** + **Headless Service**",
        "**DNS_PING + JGroups/Infinispan** replicate auth/session state",
        "InitContainer caches Quarkus build to **PVC**; Keycloak `--optimized` start",
        "**Startup ~55 s**; any pod can complete OAuth flow",
    ],
    height=740,
)

st.divider()
st.write("📄 Download the static PDF version:  ", "[resume.pdf](resume.pdf)")

import os, re, time, hmac, bcrypt
from pathlib import Path
from PIL import Image
import streamlit as st
from streamlit.components.v1 import html as html_component

# --------------------------- Config ---------------------------
st.set_page_config(page_title="Architecture Improvement", page_icon="🧭", layout="wide")
ASSETS = Path("assets")

ACCESS_CODE_HASH = os.getenv("ACCESS_CODE_HASH", "") or st.secrets.get("ACCESS_CODE_HASH", "")
ACCESS_CODE      = os.getenv("ACCESS_CODE", "")      or st.secrets.get("ACCESS_CODE", "")

# --------------------------- Auth -----------------------------
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

# -------------------------- Helpers ---------------------------
def kpi(label, value, sub=""):
    c = st.container(border=True)
    c.metric(label, value, sub)

def load_image(*names: str):
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

def _extract_mxgraph_div(html_text: str) -> str | None:
    m = re.search(r'(<div[^>]+class="mxgraph"[^>]*data-mxgraph=.*?</div>)', html_text, re.S | re.I)
    return m.group(1) if m else None

def show_drawio_html(filename: str, height: int = 640, scrolling: bool = False) -> bool:
    """
    Render draw.io export by extracting the mxgraph div and feeding it to viewer-static.min.js.
    Works more reliably inside Streamlit than embedding the whole exported HTML.
    """
    p = ASSETS / filename
    if not p.exists():
        return False
    try:
        raw = p.read_text(encoding="utf-8", errors="ignore")
        mx = _extract_mxgraph_div(raw)
        if not mx:
            return False
        wrapper = f"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://viewer.diagrams.net/js/viewer-static.min.js"></script>
<style>html,body,#holder{{height:100%;margin:0}} #holder>div{{height:100%}}</style>
</head><body><div id="holder">{mx}</div></body></html>
"""
        html_component(wrapper, height=height, scrolling=scrolling)
        return True
    except Exception:
        return False

def show_drawio_or_image(html_name: str, *fallback_images: str, height: int = 640):
    if not show_drawio_html(html_name, height=height):
        img = load_image(*fallback_images)
        if img:
            st.image(img, use_column_width=True)
        else:
            st.warning(f"Diagram not found: assets/{html_name}")

# ---------------------- Sidebar gate --------------------------
with st.sidebar:
    st.header("🔒 Access")
    st.caption("**Hint:** the access code is printed at the **top-right of my resume**.")
    if not is_authed():
        pin = st.text_input("Enter access code", type="password")
        if st.button("Unlock"):
            if verify_code(pin):
                st.success("Welcome!")
                time.sleep(0.4)
                st.rerun()
            else:
                st.error("Wrong code")
        st.stop()
    st.success("Access granted")

# --------------------------- Header ---------------------------
st.title("Architecture Improvement")
st.caption("Three recent infrastructure transformations with measurable impact.")

# ======= Case 1 — FE Storage SPA → FE on AKS (BFF) =======
st.subheader("1) **F/E Storage Account + B/E on AKS (SPA)** → **F/E containerized on AKS with B/E (BFF)**")

tab_before, tab_after = st.tabs(["Before", "After"])
with tab_before:
    c1, c2 = st.columns([1.2, 0.8], vertical_alignment="top")
    with c1:
        show_drawio_or_image("fe_before.html", "fe_before.webp", height=620)
    with c2:
        bullet_box("Before (SPA + public API)", [
            "Frontend hosted on **Storage static website**",
            "Browser calls **public API** through the edge → CORS & more hops",
            "Azure Front Door routes to Storage (FE) and AKS (API) separately",
        ])
        a1, a2 = st.columns(2)
        with a1: kpi("Latency", "↑", "edge hops + CORS")
        with a2: kpi("Surface", "wider", "public API exposed")

with tab_after:
    c1, c2 = st.columns([1.2, 0.8], vertical_alignment="top")
    with c1:
        show_drawio_or_image("fe_after.html", "fe_after.webp", height=620)
    with c2:
        bullet_box("After (BFF on AKS)", [
            "FE containerized & deployed **with B/E** in the same AKS cluster",
            "**Single origin** via AFD → AKS over Private Link (**no CORS**)",
            "FE ↔ BE are **in-cluster** service-to-service (**BFF** pattern)",
            "Simpler deploys / rollback / observability",
        ])
        a1, a2 = st.columns(2)
        with a1: kpi("Latency", "↓", "fewer edge hops")
        with a2: kpi("Security", "↑", "no public API")

# Traffic Flow + Highlights side-by-side
lf, rt = st.columns(2, vertical_alignment="top")
with lf:
    st.markdown("#### Traffic Flow (Before vs. After)")
    flow = st.container(border=True)
    flow.markdown("""
1) **Client → Azure FD**  
   - Browser → Azure FD with WAF (TLS at AFD)  
   - **Before:** Two hosts (F/E & B/E) ⇒ CORS required  
   - **After:** Single host ⇒ no CORS for web ↔ API  

2) **AFD → Origin via Private Link**  
   - AFD → **PE (consumer)** → **PLS (provider)** performs **SNAT**  
   - **Before (F/E origin):** PLS → **Storage static website** (HTML/JS/CSS)  
   - **After (AKS origin):** PLS → **Internal Standard LB** → **Nginx Ingress (AKS)**  

3) **App ↔ API path**  
   - **Before:** Browser JS calls API directly via AFD to AKS  
   - **After:** FE server (pods) calls BE **in-cluster** via `ClusterIP/DNS`  
     `http://be-svc.<ns>.svc.cluster.local`  

4) **AKS egress** → **Azure Firewall** (SNAT to public IP)  

5) **DNS Proxy** → Azure DNS / Private Resolver for Private Link names
""")

with rt:
    st.markdown("#### Transformation Highlights")
    hi = st.container(border=True)
    hi.markdown("""
**Performance & Cost**  
- In-cluster FE→BE calls cut Internet/edge hops ⇒ **lower latency**  
- **Egress savings**: FE↔BE stays inside the cluster  

**Security**  
- Public API removed (API is **ClusterIP-only**)  
- Origin reachable only via **AFD → PE → PLS → ILB → Ingress**  
- Single controlled egress (Firewall **SNAT**) ⇒ simpler allow-listing & audit  

**DevOps & Observability**  
- Unified **CI/CD** & rollbacks; cleaner **health probes / logging**
""")

st.divider()

# ======= Case 2 — Docker Hub → Nexus proxy cache =======
st.subheader("2) **Direct pulls from Docker Hub** → **In-cluster Nexus Docker proxy (pull-through cache)**")
tab_b2, tab_a2 = st.tabs(["Before", "After"])

with tab_b2:
    c1, c2 = st.columns([1.2, 0.8], vertical_alignment="top")
    with c1:
        show_drawio_or_image("nexus_before.html", "nexus_before.webp", height=620)
    with c2:
        bullet_box("Before (external dependency)", [
            "Every node/pod pulled images from **Docker Hub** via Firewall SNAT",
            "Hit **429 rate-limits** during AKS upgrades",
            "Slow cold pulls; no in-cluster cache",
        ])

with tab_a2:
    c1, c2 = st.columns([1.2, 0.8], vertical_alignment="top")
    with c1:
        show_drawio_or_image("nexus_after.html", "nexus_after.webp", height=620)
    with c2:
        bullet_box("After (internal proxy cache)", [
            "**Nexus Docker proxy** inside AKS (pull-through cache via Ingress)",
            "Manifests retargeted to `docker-group.dev.sgarch.net` (GitOps)",
            "Only **cache-miss** goes to Docker Hub; reliable upgrades",
            "Private registry endpoint improves control & auditability",
        ])
        a1, a2 = st.columns(2)
        with a1: kpi("429 errors", "0", "during upgrades")
        with a2: kpi("Cold pull", "~60 ms", "cached layer")

st.divider()

# ======= Case 3 — Keycloak Deployment → StatefulSet + cache =======
st.subheader("3) **Keycloak Deployment + sticky sessions** → **StatefulSet clustering + build cache (PVC)**")
tab_b3, tab_a3 = st.tabs(["Before", "After"])

with tab_b3:
    c1, c2 = st.columns([1.2, 0.8], vertical_alignment="top")
    with c1:
        show_drawio_or_image("keycloak_before.html", "keycloak_before.webp", height=620)
    with c2:
        bullet_box("Before (no clustering)", [
            "Ran as a Deployment; sticky sessions at ingress",
            "Quarkus build on each start → **~6 min cold start**",
            "Multi-pod token exchange failed at times (no shared cache)",
        ])

with tab_a3:
    c1, c2 = st.columns([1.2, 0.8], vertical_alignment="top")
    with c1:
        show_drawio_or_image("keycloak_after.html", "keycloak_after.webp", height=620)
    with c2:
        bullet_box("After (HA + fast start)", [
            "Migrated to **StatefulSet** + **Headless Service**",
            "**DNS_PING + JGroups/Infinispan** replicate auth/session state",
            "InitContainer caches Quarkus build to **PVC**; Keycloak `--optimized` start",
            "**Startup ~55 s**; any pod can complete OAuth flow",
        ])
        a1, a2, a3 = st.columns(3)
        with a1: kpi("Startup", "~55 s", "from 6+ min")
        with a2: kpi("HA", "Multi-pod", "podAntiAffinity + PDB")
        with a3: kpi("Auth errors", "0", "during rollout")

st.divider()
st.write("📄 Download the static PDF version:  ", "[resume.pdf](resume.pdf)")

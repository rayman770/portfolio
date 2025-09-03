# app.py
import os
import time
import hmac
import bcrypt
import re
from pathlib import Path
from PIL import Image

import streamlit as st
from streamlit.components.v1 import html as html_component


# --------------------------- Config ---------------------------
st.set_page_config(page_title="Architecture Improvement", page_icon="🧭", layout="wide")
ASSETS = Path("assets")

# light spacing trim
st.markdown(
    """
<style>
/* tighten some paddings */
.block-container { padding-top: 1.2rem; }
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMetric"]) { margin-top: .25rem; }
</style>
""",
    unsafe_allow_html=True,
)

# Access control (choose one in Secrets)
ACCESS_CODE_HASH = os.getenv("ACCESS_CODE_HASH", "") or st.secrets.get("ACCESS_CODE_HASH", "")
ACCESS_CODE      = os.getenv("ACCESS_CODE", "")      or st.secrets.get("ACCESS_CODE", "")


# --------------------------- Auth -----------------------------
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


def is_authed():
    if st.session_state.get("authed"):
        return True
    qp = st.experimental_get_query_params()
    if "code" in qp and qp["code"]:
        return verify_code(qp["code"][0])
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


# ---------------------- draw.io rendering ---------------------
def _extract_mxgraph_div(html_text: str) -> str | None:
    """
    Extract the <div class="mxgraph" ... data-mxgraph="..."></div> block.
    Robust to single/double quotes and extra classes/attributes.
    """
    pat = (
        r'(<div[^>]*class=(?:"[^"]*\\bmxgraph\\b[^"]*"|\'[^\']*\\bmxgraph\\b[^\']*\')'
        r'[^>]*data-mxgraph=(?:"[^"]*"|\'[^\']*\')[^>]*>\\s*</div>)'
    )
    m = re.search(pat, html_text, re.S | re.I)
    return m.group(1) if m else None


def _inject_base_tag(doc: str) -> str:
    """
    Ensure the document has a <base href="https://viewer.diagrams.net/"> inside <head>.
    Needed so viewer-static and Azure icon assets resolve properly.
    """
    if "<base " in doc.lower():
        return doc
    return re.sub(
        r"(<head[^>]*>)",
        r'\1<base href="https://viewer.diagrams.net/">',
        doc,
        count=1,
        flags=re.I,
    )


def render_drawio(filename: str, height: int = 640, scrolling: bool = False) -> bool:
    """
    1) Try to wrap the <div class="mxgraph" ...> with viewer-static and a <base> tag (best).
    2) Fallback to embedding the full exported HTML with <base> injected.
    """
    p = ASSETS / filename
    if not p.exists():
        return False
    try:
        raw = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    mx = _extract_mxgraph_div(raw)
    if mx:
        wrapper = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<base href="https://viewer.diagrams.net/">
<script src="https://viewer.diagrams.net/js/viewer-static.min.js"></script>
<style>html,body,#holder{{height:100%;margin:0}} #holder>div{{height:100%}}</style>
</head>
<body>
  <div id="holder">{mx}</div>
</body>
</html>"""
        html_component(wrapper, height=height, scrolling=scrolling)
        return True

    raw_with_base = _inject_base_tag(raw)
    html_component(raw_with_base, height=height, scrolling=True)
    return True


def show_drawio_or_image(html_name: str, *fallback_images: str, height: int = 640):
    if not render_drawio(html_name, height=height):
        img = load_image(*fallback_images)
        if img:
            st.image(img, use_column_width=True)
        else:
            st.warning(f"Diagram not found or unreadable: assets/{html_name}")


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

    # tiny inspector to confirm files are there
    with st.expander("🛠 Assets inspector", expanded=False):
        try:
            st.json(sorted([p.name for p in ASSETS.iterdir() if p.is_file()]))
        except Exception:
            st.write("No assets/ directory?")


# --------------------------- Header ---------------------------
st.title("Architecture Improvement")
st.caption("Three recent infrastructure transformations with measurable impact.")


# ===================== Case 1 =====================
st.subheader("1) **F/E Storage Account + B/E on AKS (SPA)** → **F/E containerized on AKS with B/E (BFF)**")
tab_b1, tab_a1 = st.tabs(["Before", "After"])

with tab_b1:
    c1, c2 = st.columns([1.2, 0.8], vertical_alignment="top")
    with c1:
        show_drawio_or_image("fe_before.html", "fe_before.webp")
    with c2:
        bullet_box("Before (SPA + public API)", [
            "Frontend hosted on **Storage static website**",
            "Browser calls **public API** through the edge → CORS & more hops",
            "Azure Front Door routes to Storage (FE) and AKS (API) separately",
        ])
        a1, a2 = st.columns(2)
        with a1: kpi("Latency", "↑", "edge hops + CORS")
        with a2: kpi("Surface", "wider", "public API exposed")

with tab_a1:
    c1, c2 = st.columns([1.2, 0.8], vertical_alignment="top")
    with c1:
        show_drawio_or_image("fe_after.html", "fe_after.webp")
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

lf, rt = st.columns(2, vertical_alignment="top")
with lf:
    st.markdown("#### Traffic Flow (Before vs. After)")
    flow = st.container(border=True)
    flow.markdown(
        """
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
"""
    )

with rt:
    st.markdown("#### Transformation Highlights")
    hi = st.container(border=True)
    hi.markdown(
        """
**Performance & Cost**  
- In-cluster FE→BE calls cut Internet/edge hops ⇒ **lower latency**  
- **Egress savings**: FE↔BE stays inside the cluster  

**Security**  
- Public API removed (API is **ClusterIP-only**)  
- Origin reachable only via **AFD → PE → PLS → ILB → Ingress**  
- Single controlled egress (Firewall **SNAT**) ⇒ simpler allow-listing & audit  

**DevOps & Observability**  
- Unified **CI/CD** & rollbacks; cleaner **health probes / logging**
"""
    )

st.divider()

# ===================== Case 2 =====================
st.subheader("2) **Direct pulls from Docker Hub** → **In-cluster Nexus Docker proxy (pull-through cache)**")
tab_b2, tab_a2 = st.tabs(["Before", "After"])

with tab_b2:
    c1, c2 = st.columns([1.2, 0.8], vertical_alignment="top")
    with c1:
        show_drawio_or_image("nexus_before.html", "nexus_before.webp")
    with c2:
        bullet_box("Before (external dependency)", [
            "Every node/pod pulled images from **Docker Hub** via Firewall SNAT",
            "Hit **429 rate-limits** during AKS upgrades",
            "Slow cold pulls; no in-cluster cache",
        ])

with tab_a2:
    c1, c2 = st.columns([1.2, 0.8], vertical_alignment="top")
    with c1:
        show_drawio_or_image("nexus_after.html", "nexus_after.webp")
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

# ===================== Case 3 =====================
st.subheader("3) **Keycloak Deployment + sticky sessions** → **StatefulSet clustering + build cache (PVC)**")
tab_b3, tab_a3 = st.tabs(["Before", "After"])

with tab_b3:
    c1, c2 = st.columns([1.2, 0.8], vertical_alignment="top")
    with c1:
        show_drawio_or_image("keycloak_before.html", "keycloak_before.webp")
    with c2:
        bullet_box("Before (no clustering)", [
            "Ran as a Deployment; sticky sessions at ingress",
            "Quarkus build on each start → **~6 min cold start**",
            "Multi-pod token exchange failed at times (no shared cache)",
        ])

with tab_a3:
    c1, c2, _ = st.columns([1.2, 0.8, 0.01], vertical_alignment="top")
    with c1:
        show_drawio_or_image("keycloak_after.html", "keycloak_after.webp")
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

import os, time, hmac, bcrypt, re
from typing import Optional
from pathlib import Path
import streamlit as st
from streamlit.components.v1 import html as html_component

# ============================ Config ============================
st.set_page_config(page_title="Architecture Improvement", page_icon="🧭", layout="wide")
ASSETS = Path("assets")

# Per-file heights so diagrams fit without internal scrollbars
HEIGHTS = {
    "fe_before.html": 460,
    "fe_after.html": 460,
    "nexus_before.html": 820,
    "nexus_after.html": 820,
    "keycloak_before.html": 880,
    "keycloak_after.html": 880,
}

# light spacing trim
st.markdown("""
<style>
.block-container { padding-top: 1.2rem; }
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMetric"]) { margin-top: .25rem; }
</style>
""", unsafe_allow_html=True)

# Access control (choose one in Secrets)
ACCESS_CODE_HASH = os.getenv("ACCESS_CODE_HASH", "") or st.secrets.get("ACCESS_CODE_HASH", "")
ACCESS_CODE      = os.getenv("ACCESS_CODE", "")      or st.secrets.get("ACCESS_CODE", "")

# ============================ Auth ==============================
def is_authed():
    if st.session_state.get("authed"):
        return True
    # use modern API (avoid deprecation)
    qp = st.query_params
    if "code" in qp and qp["code"]:
        # qp["code"] is a string
        return verify_code(qp["code"])
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

# =========================== Helpers ============================
def kpi(label, value, sub=""):
    c = st.container(border=True)
    c.metric(label, value, sub)

def bullet_box(title: str, bullets: list[str]):
    c = st.container(border=True)
    c.markdown(f"**{title}**")
    for b in bullets:
        c.markdown(f"- {b}")
    return c

def _extract_mxgraph_div(html_text: str) -> Optional[str]:
    """
    Find a <div ... class="mxgraph" ... data-mxgraph="..."></div>
    Accepts single/double quotes, class order, extra classes, and whitespace.
    """
    pat = r'(<div[^>]*class=(?:"[^"]*\bmxgraph\b[^"]*"|\'[^\']*\bmxgraph\b[^\']*\')[^>]*data-mxgraph=(?:"[^"]*"|\'[^\']*\')[^>]*>\s*</div>)'
    m = re.search(pat, html_text, re.I | re.S)
    return m.group(1) if m else None

def _inject_base_tag(doc: str) -> str:
    """Insert <base href="https://viewer.diagrams.net/"> right after <head> (once)."""
    if re.search(r"<base\s", doc, re.I):
        return doc
    return re.sub(
        r"(<head[^>]*>)",
        lambda m: m.group(1) + '<base href="https://viewer.diagrams.net/">',
        doc,
        count=1,
        flags=re.I,
    )

def _ensure_viewer_script(doc: str) -> str:
    """Make sure viewer-static.min.js is present (some exports omit it)."""
    if "viewer-static.min.js" in doc:
        return doc
    insertion = '<script src="https://viewer.diagrams.net/js/viewer-static.min.js"></script>'
    return re.sub(
        r"(</head>)",
        lambda m: insertion + m.group(1),
        doc,
        count=1,
        flags=re.I,
    )

def _prepare_full_export(doc: str) -> str:
    """For full HTML exports: add <base> and the viewer script if needed."""
    doc = _inject_base_tag(doc)
    doc = _ensure_viewer_script(doc)
    return doc

def render_drawio(filename: str, height: Optional[int] = None, scrolling: bool = False) -> bool:
    """
    Robust Draw.io/diagrams.net renderer for HTML exports.
    1) If an mxgraph <div> exists, wrap it with viewer-static and a <base>.
    2) Otherwise embed the full HTML but ensure it has a <base> and viewer script.
    """
    p = ASSETS / filename
    if not p.exists():
        return False
    try:
        raw = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    h = height or HEIGHTS.get(filename, 560)

    mx = _extract_mxgraph_div(raw)
    if mx:
        wrapper = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<base href="https://viewer.diagrams.net/">
<script src="https://viewer.diagrams.net/js/viewer-static.min.js"></script>
<style>
  html,body,#holder{{height:100%;margin:0}}
  #holder>div{{height:100%}}
  .mxgraph{{max-width:100%;border:0}}
</style>
</head>
<body>
  <div id="holder">{mx}</div>
</body>
</html>"""
        html_component(wrapper, height=h, scrolling=scrolling)
        return True

    # Fallback: full export — ensure it has what it needs
    doc = _prepare_full_export(raw)
    html_component(doc, height=h, scrolling=scrolling)
    return True

def show_drawio_or_warn(html_name: str, height: Optional[int] = None):
    ok = render_drawio(html_name, height=height, scrolling=False)
    if not ok:
        st.container(border=True).warning(f"Diagram not found or unreadable: assets/{html_name}")

# ======================== Sidebar Gate ==========================
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

    with st.expander("🛠 Assets inspector", expanded=False):
        try:
            st.json(sorted([p.name for p in ASSETS.iterdir() if p.is_file()]))
        except Exception:
            st.write("No assets/ directory?")

# ============================ Header ============================
st.title("Architecture Improvement")
st.caption("Three recent infrastructure transformations with measurable impact.")

# ============================ Case 1 ============================
st.subheader("1) F/E Storage Account + public API → F/E containerized with B/E (BFF on AKS)")
left, right = st.columns([1, 1], vertical_alignment="top")

with left:
    show_drawio_or_warn("fe_before.html")
    bullet_box("Before (SPA + public API)", [
        "Frontend hosted on **Storage static website**",
        "Browser calls **public API** through the edge → CORS & more hops",
        "Azure Front Door routes to Storage (FE) and AKS (API) separately",
    ])
    c1, c2 = st.columns(2)
    with c1: kpi("Latency", "↑", "edge hops + CORS")
    with c2: kpi("Surface", "wider", "public API exposed")

with right:
    show_drawio_or_warn("fe_after.html")
    bullet_box("After (BFF on AKS)", [
        "FE containerized & deployed **with B/E** in the same AKS cluster",
        "**Single origin** via AFD → AKS over Private Link (**no CORS**)",
        "FE ↔ BE are **in-cluster** service-to-service (**BFF** pattern)",
        "Simpler deploys / rollback / observability",
    ])
    c1, c2 = st.columns(2)
    with c1: kpi("Latency", "↓", "fewer edge hops")
    with c2: kpi("Security", "↑", "no public API")

st.divider()

# ============================ Case 2 ============================
st.subheader("2) Direct pulls from Docker Hub → In-cluster Nexus Docker proxy (pull-through cache)")
l2, r2 = st.columns([1, 1], vertical_alignment="top")

with l2:
    show_drawio_or_warn("nexus_before.html")
    bullet_box("Before (external dependency)", [
        "Every node/pod pulled images from **Docker Hub** via Firewall SNAT",
        "Hit **429 rate-limits** during AKS upgrades",
        "Slow cold pulls; no in-cluster cache",
    ])

with r2:
    show_drawio_or_warn("nexus_after.html")
    bullet_box("After (internal proxy cache)", [
        "**Nexus Docker proxy** inside AKS (pull-through cache via Ingress)",
        "Manifests retargeted to `docker-group.dev.sgarch.net` (GitOps)",
        "Only **cache-miss** goes to Docker Hub; reliable upgrades",
        "Private registry endpoint improves control & auditability",
    ])
    c1, c2 = st.columns(2)
    with c1: kpi("429 errors", "0", "during upgrades")
    with c2: kpi("Cold pull", "~60 ms", "cached layer")

st.divider()

# ============================ Case 3 ============================
st.subheader("3) Keycloak Deployment + sticky sessions → StatefulSet clustering + build cache (PVC)")
l3, r3 = st.columns([1, 1], vertical_alignment="top")

with l3:
    show_drawio_or_warn("keycloak_before.html")
    bullet_box("Before (no clustering)", [
        "Ran as a Deployment; sticky sessions at ingress",
        "Quarkus build on each start → **~6 min cold start**",
        "Multi-pod token exchange failed at times (no shared cache)",
    ])

with r3:
    show_drawio_or_warn("keycloak_after.html")
    bullet_box("After (HA + fast start)", [
        "Migrated to **StatefulSet** + **Headless Service**",
        "**DNS_PING + JGroups/Infinispan** replicate auth/session state",
        "InitContainer caches Quarkus build to **PVC**; Keycloak `--optimized` start",
        "**Startup ~55 s**; any pod can complete OAuth flow",
    ])
    c1, c2, c3 = st.columns(3)
    with c1: kpi("Startup", "~55 s", "from 6+ min")
    with c2: kpi("HA", "Multi-pod", "podAntiAffinity + PDB")
    with c3: kpi("Auth errors", "0", "during rollout")

st.divider()
st.write("📄 Download the static PDF version:  ", "[resume.pdf](resume.pdf)")

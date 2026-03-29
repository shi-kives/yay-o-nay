import streamlit as st
import requests
import plotly.express as px
import plotly.graph_objects as go
import time
import os
from dotenv import load_dotenv

load_dotenv(override=True)
API_BASE = os.getenv("API_BASE","http://localhost:8000")
API_KEY = os.getenv("API_KEY")
HEADERS = {"X-API-Key": API_KEY}

st.set_page_config(
    page_title="YayONay",
    page_icon="Y",
    layout="wide",
    initial_sidebar_state="expanded"
)

for key, default in {"task_id": None, "asin": None, "analyzing": False, }.items():
    if key not in st.session_state:
        st.session_state[key] = default

@st.cache_data(ttl=500)
def fetch_recommendation(asin):
    r = requests.get(f"{API_BASE}/products/{asin}/recommendation", headers=HEADERS)
    return r.json() if r.status_code == 200 else {}

@st.cache_data(ttl=500)
def fetch_score(asin):
    r = requests.get(f"{API_BASE}/products/{asin}/score", headers=HEADERS)
    return r.json() if r.status_code == 200 else {}

@st.cache_data(ttl=500)
def fetch_trends(asin):
    r = requests.get(f"{API_BASE}/prducts/{asin}/trends", headers=HEADERS)
    return r.json() if r.status_code == 200 else {}

@st.cache_data(ttl=500)
def fetch_summary(asin):
    r = requests.get(f"{API_BASE}/products/{asin}/aspects", headers=HEADERS)
    return r.json().get("summary", "") if r.status_code == 200 else ""

@st.cache_data(ttl=500)
def fetch_aspects(asin):
    r = requests.get(f"{API_BASE}/products/{asin}/aspects", headers=HEADERS)
    return r.json() if r.status_code == 200 else {}

@st.cache_data(ttl=500)
def fetch_compare(asin_a, asin_b):
    r = requests.get(f"{API_BASE}/compare", params = {"asin_a": asin_a, "asin_b": asin_b}, headers=HEADERS)
    return r.json() if r.status_code == 200 else {}

def poll_task(task_id):
    r = requests.get(f"{API_BASE}/tasks/{task_id}", headers=HEADERS)
    return r.json() if r.status_code == 200 else {}

with st.sidebar:
    st.markdown("### YayONay")
    st.caption("Paste an Amazon Product's URL to get an instant Yay or Nay verdict!")
    st.divider()

    url_input = st.text_input("Amazon Product URL", placeholder="https://www.amazon.com/dp/B09XYZ123")

    go_btn = st.button("Go", use_container_width=True, type="primary")

    if go_btn and url_input:
        resp = requests.post(f"{API_BASE}/analyze/url", json={"url": url_input}, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.task_id = data["task_id"]
            st.session_state.asin = data["asin"]
            st.session_state.analyzing = True
            st.cache_data.clear()
        else:
            st.error("Could not find the product. Please check the URL and try again!")

    st.divider()
    
    DEMO_ASINS = {
        "Demo Product A": "B000000001",
        "Demo Product B": "B000000002",
        "Demo Product C": "B000000003",
        "Demo Product D": "B000000004",
    }

    selected = st.selectbox("Or, pick a demo product", ["-"] + list(DEMO_ASINS.keys()))
    if selected != "-":
        st.session_state.asin = DEMO_ASINS[selected]
        st.session_state.analyzing = False
        st.session_state.task_id = None

if st.session_state.analyzing and st.session_state.task_id:
    STEPS = ["scraping reviews..", "storing reviews..", "running BERT..", "extracting aspects..", "generating verdict.."]
    progress_bar = st.progress(0, text="Starting analysis..")
    status_text = st.empty()

    while True:
        result = poll_task(st.session_state.task_id)
        status = result.get("status", "PENDING")

        if status == "PROGRESS":
            step = result.get("info", {}).get("step", "working")
            idx = STEPS.index(step) if step in STEPS else 0
            pct = (idx + 1)/len(STEPS)
            progress_bar.progress(pct, text=f"Step {idx+1}/{len(STEPS)}: {step}")

        elif status == "SUCCESS":
            progress_bar.progress(1.0, text="Analysis Complete!")
            st.session_state.analyzing = False
            time.sleep(0.5)
            st.rerun()

        elif status == "FAILURE":
            st.error("Analysis failed. Amazon may have blocked the scraper - try again, or use another input method.")
            st.session_state.analyzing = False
            break

        time.sleep(2)

elif st.session_state.asin and not st.session_state.analyzing:
    asin = st.session_state.asin
    
    rec = fetch_recommendation(asin)
    score_d = fetch_score(asin)
    trends = fetch_trends(asin)
    aspects = fetch_aspects(asin)
    summary = fetch_summary(asin)

    if not rec:
        st.warning("No data for this product yet. Rerun Analysis.")
        st.stop()

    verdict = rec.get("verdict", "Nay!")
    is_yay = verdict == "Yay"
    v_color = "#1D9E75" if is_yay else "#E24B4A"
    v_bg = "#E1F5EE" if is_yay else "#FCEBEB"

    st.markdown(f"""
    <div style = "padding: 24px; border-radius: 16px; background: {v_bg}; border: 2px solid {v_color}; text-align: center; margin-bottom: 24px">
        <div style="font-size:52px;font-weight:600;color:{v_color};line-height:1">
            {verdict.upper()}
        </div>
        <div style="font-size:20px;color:{v_color};margin:8px 0 4px;font-weight:500">
            {rec.get('label', '')}
        </div>
        <div style="font-size:14px;color:#555;max-width:500px;margin:0 auto">
        {rec.get('reason','')}
      </div>
      <div style="font-size:13px;color:#888;margin-top:10px">
        Score: {rec.get('score', 0):.1f}/10 &nbsp;·&nbsp;
        Confidence: {rec.get('confidence', 0):.0%} &nbsp;·&nbsp;
        Based on {score_d.get('review_count', 0)} reviews
      </div>
    </div>
    """, unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    score_val = score_d.get("score", 0)
    with m1:
        st.metric("Overall Score: ", f"{score_val:.1f} / 10")
    with m2:
        st.metric("Total reviews", score_d.get("review_count", 0))
    with m3:
        trend_dir = "-"
        if len(trends) >= 2:
            delta = trends[-1]["avg_score"] - trends[-2]["avg_score"]
            trend_dir = f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}"
        st.metric("Recent trend", trend_dir)
    
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Sentiment Distribution")
        all_aspects = aspects.get("all_aspects", {})
        pos_count = sum(1 for v in all_aspects.values() if v["sentiment"] == "positive")
        neg_count = sum(1 for v in all_aspects.values() if v["sentiment"] == "negative")
        pie_fig = px.pie(
            value = [pos_count, neg_count],
            names = ["Positive", "Negative"],
            color_discrete_sequence = ["#1D9E75", "#E24B4A"],
            hole = 0.4
        )
        pie_fig.update_layout(showlegend=True, margin=dict(t=0,b=0,l=0,r=0), height=280, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(pie_fig, use_container_width=True)

    with col2:
        st.subheader("Sentiment Trend")
        if trends:
            weeks = [t["week"] for t in trends]
            scores = [t["avg_score"] for t in trends]
            anomaly_x = [t["week"] for t in trends if t["is_anomaly"]]
            anomaly_y = [t["avg_score"] for t in trends if t["is_anomaly"]]
            trend_fig = go.Figure()
            trend_fig.add_trace(go.Scatter(
                x=weeks, y=scores, mode="lines+markers", line=dict(color="#7F77DD", width=2), name="Weekly Average"
            ))
            if anomaly_x:
                trend_fig.add_trace(go.Scatter(
                    x=anomaly_x, y=anomaly_y, mode="markers",
                    marker=dict(color="#E24B4A", size=10, symbol="circle"),
                    name="Anomaly"
                ))
            trend_fig.update_layout(
                xaxis_title="Week", yaxis_title="Score (0-10)",
                height=280, margin=dict(t=0,b=40,l=40,r=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                showlegend=True
            )
            st.plotly_chart(trend_fig, use_container_width=True)
        else:
            st.info("Not enough data for trend analysis yet.")

st.divider()

st.subheader("Feature Breakdown")
pros, cons = st.columns(2)
positives = rec.get("positives", [])
negatives = rec.get("negatives", [])
all_asp = aspects.get("all_aspects", [])

with pros:
    st.markdown("**What people love**")
    for asp in positives:
        count = all_asp.get(asp, {}).get("mention_coung", 0)
        score = all_asp.get(asp, {}).get("avg_score", 0)
        st.markdown(f"""
            <div style="padding:8px 12px;margin-bottom:6px;border-radius:8px;
                        background:#E1F5EE;border-left:3px solid #1D9E75">
              <span style="font-weight:500;color:#085041">{asp}</span>
              <span style="color:#0F6E56;font-size:12px;float:right">
                {count} mentions · +{score:.2f}
              </span>
            </div>
            """, unsafe_allow_html=True)
    
    with cons:
        st.markdown("**What people complain about**")
        for asp in negatives:
            count = all_asp.get(asp, {}).get("mention_count", 0)
            score = all_asp.get(asp, {}).get("avg_score", 0)
            st.markdown(f"""
            <div style="padding:8px 12px;margin-bottom:6px;border-radius:8px;
                        background:#FCEBEB;border-left:3px solid #E24B4A">
              <span style="font-weight:500;color:#791F1F">{asp}</span>
              <span style="color:#A32D2D;font-size:12px;float:right">
                {count} mentions · {score:.2f}
              </span>
            </div>
            """, unsafe_allow_html=True)

st.divider()

wc_col, sum_col = st.columns([1,1])

with wc_col:
    st.subheader("Word Cloud")
    wc_path = f"data/wordclouds/{asin}.png"
    if os.path.exists(wc_path):
        st.image(wc_path, use_container_width=True)
    else:
        st.info("Word cloud not generated yet.")

with sum_col:
    st.subheader("Review Summary")
    if summary:
        st.text_area("", value=summary, height=200, disabled=True)
    else:
        st.info("Summary not generated yet.")

st.divider()

st.subheader("Compare with another product")
compare_asin = st.text_input("Enter another ASIN to compare", placeholder="B000000002")

if compare_asin and compare_asin != asin:
    cmp = fetch_compare(asin, compare_asin)
    if cmp:
        asp_a = fetch_aspects(asin).get("all_aspects",{})
        asp_b = fetch_aspects(compare_asin).get("all_aspects",{})
        shared = list(set(asp_a.keys()) & set(asp_b.keys()))[::5]
        if shared:
            scores_a = [asp_a[k]["avg_score"] for k in shared]
            scores_b = [asp_b[k]["avg_score"] for k in shared]
            radar = go.Figure()
            radar.add_trace(go.Scatterpolar(r=scores_a, theta=shared, fill="toself", name=asin, line_color ="#7F77DD"))
            radar.add_trace(go.Scatterpolar(r=scores_b, theta=shared, fill="toself", name=compare_asin, line_color="#1D9E75"))
            radar.update_layout(polar=dict(radialaxis=dict(visible=True)), height=360, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(radar, use_container_width=True)
        st.metric("Semantic Similarity", f"{cmp.get('similarity', 0):.0%}")

else:
    st.markdown("""
    <div style="text-align:center;padding:80px 0;color:#888">
      <div style="font-size:48px;font-weight:600;margin-bottom:12px">YayoNay</div>
      <div style="font-size:18px">Paste an Amazon URL in the sidebar to get started</div>
    </div>
    """, unsafe_allow_html=True)
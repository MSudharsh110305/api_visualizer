import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from dashboard.queries import get_top_endpoints, get_latency_trend, get_service_dependencies
from dashboard.charts import top_endpoints_chart, latency_trend_chart, service_dependency_graph

st.set_page_config(page_title="API Visualizer Dashboard", layout="wide")

st.title("📈 API Visualizer Dashboard")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Top Endpoints")
    top_data = get_top_endpoints()
    if top_data:
        st.plotly_chart(top_endpoints_chart(top_data), use_container_width=True)
    else:
        st.info("No data yet.")

with col2:
    st.subheader("Latency Trend")
    lat_data = get_latency_trend()
    if lat_data:
        st.plotly_chart(latency_trend_chart(lat_data), use_container_width=True)
    else:
        st.info("No data yet.")

st.subheader("Service Dependencies")
deps = get_service_dependencies()
if deps:
    st.plotly_chart(service_dependency_graph(deps), use_container_width=True)
else:
    st.info("No dependency data yet.")

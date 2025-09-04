import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from dashboard.queries import get_top_endpoints, get_latency_trend, get_service_dependencies, get_detailed_endpoint_stats, get_data_transfer_stats
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

# Detailed Endpoint Metrics
st.subheader("📊 Detailed Endpoint Metrics")
detailed_data = get_detailed_endpoint_stats()
if detailed_data:
    import pandas as pd
    df = pd.DataFrame(detailed_data, columns=[
        'Endpoint', 'Method', 'Service', 'Requests', 'Avg Latency (ms)', 
        'Max Latency (ms)', 'Min Latency (ms)', 'Avg Request Size', 'Avg Response Size', 
        'Total Response Bytes', 'Errors'
    ])
    
    # Format the dataframe for better readability
    df['Avg Latency (ms)'] = df['Avg Latency (ms)'].round(1)
    df['Max Latency (ms)'] = df['Max Latency (ms)'].round(1)
    df['Min Latency (ms)'] = df['Min Latency (ms)'].round(1)
    df['Avg Request Size'] = df['Avg Request Size'].round(0)
    df['Avg Response Size'] = df['Avg Response Size'].round(0)
    
    st.dataframe(df, use_container_width=True)
else:
    st.info("No detailed endpoint data available.")

# Data Transfer Statistics
st.subheader("📡 Data Transfer Statistics") 
transfer_stats = get_data_transfer_stats()
if transfer_stats and transfer_stats[4]:
    col1, col2, col3, col4 = st.columns(4)
    
    total_requests = transfer_stats[4] or 0
    total_request_bytes = transfer_stats[0] or 0
    total_response_bytes = transfer_stats[1] or 0
    avg_response_size = transfer_stats[3] or 0
    
    col1.metric("Total Requests", f"{total_requests:,}")
    col2.metric("Total Request Data", f"{total_request_bytes:,} bytes")
    col3.metric("Total Response Data", f"{total_response_bytes:,} bytes") 
    col4.metric("Avg Response Size", f"{avg_response_size:.0f} bytes")
else:
    st.info("No data transfer statistics available.")

# Performance Overview
st.subheader("⚡ Performance Overview")
if detailed_data:
    total_reqs = sum(row[3] for row in detailed_data)
    total_errors = sum(row[10] for row in detailed_data)
    avg_latency = sum(row[4] * row[3] for row in detailed_data) / total_reqs if total_reqs > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Success Rate", f"{((total_reqs - total_errors) / total_reqs * 100):.1f}%" if total_reqs > 0 else "0%")
    col2.metric("Error Rate", f"{(total_errors / total_reqs * 100):.1f}%" if total_reqs > 0 else "0%")
    col3.metric("Weighted Avg Latency", f"{avg_latency:.1f} ms")
    col4.metric("Total Endpoints", len(detailed_data))

# Manual refresh button (optional)
if st.button("🔄 Refresh Dashboard"):
    st.rerun()

# ✅ REMOVED: st.rerun() - This was causing continuous refresh!

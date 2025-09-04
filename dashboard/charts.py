import plotly.express as px
import plotly.graph_objects as go
import networkx as nx

def latency_trend_chart(data):
    times = [row[0] for row in data]
    lat = [row[1] for row in data]
    fig = px.line(x=times, y=lat, title="Average Latency Over Time", labels={'x':'Time Bucket', 'y':'Latency (ms)'})
    return fig

def top_endpoints_chart(data):
    names = [f"{row[2]} {row[1]} {row[0]}" for row in data]
    counts = [row[3] for row in data]
    fig = px.bar(x=names, y=counts, title="Top Endpoints by Request Count", labels={'x':'Endpoint', 'y':'Request Count'})
    fig.update_xaxes(tickangle=45)
    return fig

def service_dependency_graph(data):
    G = nx.DiGraph()
    for dep in data:
        G.add_edge(dep['caller_service'], dep['target_service'], weight=dep['call_count'])
    pos = nx.spring_layout(G)
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), hoverinfo='none', mode='lines')
    node_x = []
    node_y = []
    text = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        text.append(node)
    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers+text', text=text,
        textposition="top center", hoverinfo='text', marker=dict(size=20, color='skyblue')
    )
    fig = go.Figure(data=[edge_trace, node_trace], layout=go.Layout(title="Service Dependency Graph", showlegend=False))
    return fig

# dashboards/memory.py
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
from config import COLOR_MEM, COLOR_SWAP, COLOR_PROCESS

def render_memory_dashboard(st, df, parse_process_column):
    st.subheader("Memory Analysis (512GB Capacity)")
    
    # 1. Memory Graph
    fig_mem = go.Figure()

    # Memory Area
    fig_mem.add_trace(go.Scatter(
        x=df['Timestamp'], y=df['Usage(%)'], 
        name='Physical Memory (%)', 
        mode='lines',
        line=dict(color=COLOR_MEM, width=2),
        fill='tozeroy'
    ))

    # Swap Line
    fig_mem.add_trace(go.Scatter(
        x=df['Timestamp'], y=df['Swap_Usage(%)'], 
        name='Swap Usage (%)', 
        mode='lines',
        line=dict(color=COLOR_SWAP, width=2)
    ))

    # Swap Start Annotation
    swap_start = df[df['Swap_Usage(%)'] > 1]['Timestamp'].min()
    if pd.notnull(swap_start):
        fig_mem.add_vline(x=swap_start, line_width=2, line_dash="dash", line_color="red", annotation_text="Swap Started")
        fig_mem.add_vrect(x0=swap_start, x1=df['Timestamp'].max(), fillcolor="red", opacity=0.1, layer="below", line_width=0)

    # Min/Max Annotations
    if not df.empty:
        min_mem_idx = df['Used(GB)'].idxmin()
        max_mem_idx = df['Used(GB)'].idxmax()
        if max_mem_idx > min_mem_idx:
             # Min point
            fig_mem.add_annotation(x=df.loc[min_mem_idx, 'Timestamp'], y=df.loc[min_mem_idx, 'Usage(%)'],
                                text="Start", showarrow=True, arrowhead=1)
            # Max point
            fig_mem.add_annotation(x=df.loc[max_mem_idx, 'Timestamp'], y=df.loc[max_mem_idx, 'Usage(%)'],
                                text="Peak", showarrow=True, arrowhead=1)

    fig_mem.update_layout(
        title="Physical Memory (Blue) vs Swap (Orange)",
        yaxis=dict(title="Usage (%)", range=[0, 100]),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_mem, use_container_width=True)
    
    st.divider()
    
    # Top 3 Memory Processes
    st.subheader("🏆 Top 3 Heavy Memory Processes (Peak Usage)")
    if 'Top5_Memory_MB' in df.columns:
        top_mem_df = parse_process_column(df['Top5_Memory_MB'])
        top3 = top_mem_df.head(3)
        
        if not top3.empty:
            fig_bar = px.bar(top3, x='Process', y='Max_Value', 
                             title="Peak Memory Usage by Process (MB)", 
                             labels={'Max_Value': 'Peak Memory (MB)'}, text_auto='.0f')
            fig_bar.update_traces(marker_color=COLOR_PROCESS)
            st.plotly_chart(fig_bar, use_container_width=True)
            
            with st.expander("See Top 10 Details"):
                st.dataframe(top_mem_df.head(10))
        else:
            st.warning("No process data available.")

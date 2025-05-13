import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, time
import matplotlib as mpl

st.set_page_config(layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("df_5min.csv", parse_dates=['Device Date/Time'])
    df['Device Date/Time'] = df['Device Date/Time'].dt.tz_localize(None)
    return df

df = load_data()

# Sidebar filters
st.sidebar.header("Filter by Time Range")
start_date = st.sidebar.date_input("Start Date", df['Device Date/Time'].min().date())
start_time_input = st.sidebar.time_input("Start Time", time(0, 0))
end_date = st.sidebar.date_input("End Date", df['Device Date/Time'].max().date())
end_time_input = st.sidebar.time_input("End Time", time(23, 59))

start_datetime = datetime.combine(start_date, start_time_input)
end_datetime = datetime.combine(end_date, end_time_input)

df_filtered = df[(df['Device Date/Time'] >= start_datetime) & (df['Device Date/Time'] <= end_datetime)]

# Load external data
payload_df = pd.read_csv("payload_df.csv", parse_dates=['cycle_start_time'])
channel_summary_tab = pd.read_csv("channel_summary_tab.csv", parse_dates=['cycle_start_time'])

channel_summary_tab['cycle_start_time'] = pd.to_datetime(channel_summary_tab['cycle_start_time'])

# Filter based on time
filtered_sql_df = channel_summary_tab[
    (channel_summary_tab['cycle_start_time'] >= start_datetime) &
    (channel_summary_tab['cycle_start_time'] <= end_datetime)
]

# Channel code selection
channel_codes = filtered_sql_df['channel_code'].unique()
selected_channel = st.sidebar.selectbox("Select Channel Code", sorted(channel_codes) if len(channel_codes) > 0 else ["None"])

filtered_channel_df = filtered_sql_df[filtered_sql_df['channel_code'] == selected_channel]

# Round and aggregate payload
payload_df['cycle_start_time'] = pd.to_datetime(payload_df['cycle_start_time'])
payload_df['cycle_start_time_5min'] = payload_df['cycle_start_time'].dt.floor('5T')

agg_payload_5min = (
    payload_df
    .groupby('cycle_start_time_5min')['avg_payload']
    .agg(sum_payload='sum', count_payload='count', avg_payload='mean')
    .reset_index()
)

filtered_channel_df = pd.merge(
    filtered_channel_df,
    agg_payload_5min,
    left_on='cycle_start_time',
    right_on='cycle_start_time_5min',
    how='left'
)

# Merge for final analysis
merged_df = pd.merge(
    df_filtered,
    filtered_channel_df,
    how='inner',
    left_on='Device Date/Time',
    right_on='cycle_start_time'
)

final_merged_df = pd.merge(
    merged_df,
    filtered_channel_df,
    left_on='Device Date/Time',
    right_on='cycle_start_time_5min',
    how='inner'
)

# Dashboard Title
st.title("EX3600 Excavator - Fuel Use & Emission Dashboard")

# KPIs
col1, col2, col3 = st.columns(3)
col1.metric("Total Fuel Used (L)", f"{df_filtered['FUEL USED DELTA'].sum():.2f}")
col2.metric("Estimated CO₂ (kg)", f"{df_filtered['Estimated CO2 (kg)'].sum():.2f}")
col3.metric("Avg Engine Load (%)", f"{df_filtered['ENGINE LOAD'].mean():.1f}")

# Graphs Section
# --- Row 1 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Fuel Rate Over Time")
    fig = px.line(df_filtered, x='Device Date/Time', y='FUEL RATE', title='Fuel Rate (L/hr)')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Engine Load vs Fuel Rate")
    fig2 = px.scatter(df_filtered, x='ENGINE LOAD', y='FUEL RATE', color='Estimated CO2 (kg)',
                      title="Engine Load vs Fuel Rate (CO₂ colored)")
    st.plotly_chart(fig2, use_container_width=True)

# --- Row 2 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Damage vs Fuel Rate")
    fig3 = px.scatter(merged_df, x='damage', y='FUEL RATE', color='Estimated CO2 (kg)',
                      title="Damage vs Fuel Rate (CO₂ colored)")
    st.plotly_chart(fig3, use_container_width=True)

with col2:
    st.subheader("Life vs Fuel Rate")
    fig4 = px.scatter(merged_df, x='life', y='FUEL RATE', color='Estimated CO2 (kg)',
                      title="Life vs Fuel Rate (CO₂ colored)")
    st.plotly_chart(fig4, use_container_width=True)

# --- Row 3 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Normal Distribution of 'Life'")
    fig6, ax = plt.subplots(figsize=(6, 4))
    sns.histplot(filtered_channel_df['life'].dropna(), kde=True, stat="density", bins=30, ax=ax, color='skyblue')
    ax.set_title("Distribution of Life with Bell Curve")
    ax.set_xlabel("Life")
    ax.set_ylabel("Density")
    fig6.tight_layout()
    st.pyplot(fig6)

with col2:
    st.subheader("Heatmap: Intake Temp vs Fuel Rate")
    heatmap_df = df_filtered[['INTAKE TEMP', 'FUEL RATE']].dropna()
    fig5, ax = plt.subplots(figsize=(6, 4))
    sns.histplot(data=heatmap_df, x='INTAKE TEMP', y='FUEL RATE', bins=30, ax=ax, cmap='YlOrRd')
    ax.set_title("Heatmap: Intake Temp vs Fuel Rate")
    fig5.tight_layout()
    st.pyplot(fig5)

# --- Row 4 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Throttle vs Fuel Rate")
    if 'THROTTLE' in df_filtered.columns:
        fig_throttle = px.scatter(df_filtered, x='THROTTLE', y='FUEL RATE',
                                  title="Throttle vs Fuel Rate")
        st.plotly_chart(fig_throttle, use_container_width=True)
    else:
        st.write("Throttle data is not available.")

with col2:
    st.subheader("Engine Speed vs Fuel Rate")
    if 'ENGINE SPEED' in df_filtered.columns:
        fig_speed = px.scatter(df_filtered, x='ENGINE SPEED', y='FUEL RATE',
                               title="Engine Speed vs Fuel Rate")
        st.plotly_chart(fig_speed, use_container_width=True)
    else:
        st.write("Engine speed data is not available.")

# --- Row 5 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Speed vs Fuel Rate")
    if 'Speed' in df_filtered.columns:
        fig_speed_fuel = px.scatter(df_filtered, x='Speed', y='FUEL RATE',
                                    title="Speed vs Fuel Rate")
        st.plotly_chart(fig_speed_fuel, use_container_width=True)
    else:
        st.write("Speed data is not available.")

with col2:
    st.subheader("Cumulative Fuel Used Over Time")
    if not df_filtered.empty:
        df_filtered['Cumulative Fuel'] = df_filtered['FUEL USED DELTA'].cumsum()
        fig_cumulative = px.line(df_filtered, x='Device Date/Time', y='Cumulative Fuel',
                                  title="Cumulative Fuel Used Over Time")
        st.plotly_chart(fig_cumulative, use_container_width=True)
    else:
        st.write("No data available for the selected time range.")

# --- Payload section ---
st.markdown("## Payload vs Fuel Metrics")

if not filtered_channel_df.empty and 'FUEL RATE' in final_merged_df.columns and 'FUEL USED DELTA' in final_merged_df.columns:

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Sum Payload vs Fuel Rate")
        fig_payload1 = px.scatter(final_merged_df, x='sum_payload', y='FUEL RATE')
        st.plotly_chart(fig_payload1, use_container_width=True)

    with col2:
        st.subheader("Count Payload vs Fuel Rate")
        fig_payload2 = px.scatter(final_merged_df, x='count_payload', y='FUEL RATE')
        st.plotly_chart(fig_payload2, use_container_width=True)

    with col3:
        st.subheader("Avg Payload vs Fuel Rate")
        fig_payload3 = px.scatter(final_merged_df, x='avg_payload', y='FUEL RATE')
        st.plotly_chart(fig_payload3, use_container_width=True)

    col4, col5, col6 = st.columns(3)

    with col4:
        st.subheader("Sum Payload vs Fuel Used")
        fig_payload4 = px.scatter(final_merged_df, x='sum_payload', y='FUEL USED DELTA')
        st.plotly_chart(fig_payload4, use_container_width=True)

    with col5:
        st.subheader("Count Payload vs Fuel Used")
        fig_payload5 = px.scatter(final_merged_df, x='count_payload', y='FUEL USED DELTA')
        st.plotly_chart(fig_payload5, use_container_width=True)

    with col6:
        st.subheader("Avg Payload vs Fuel Used")
        fig_payload6 = px.scatter(final_merged_df, x='avg_payload', y='FUEL USED DELTA')
        st.plotly_chart(fig_payload6, use_container_width=True)

    # Apply a clean and professional style
    mpl.rcParams.update({
        'axes.titlesize': 12,
        'axes.labelsize': 10,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'axes.grid': True,
        'grid.alpha': 0.3,
        'grid.color': '#cccccc',
        'axes.facecolor': 'white',
        'axes.edgecolor': '#dddddd',
        'figure.facecolor': 'white'
    })

    st.subheader("Normal Distribution of 'No. of Passes'")
    fig_payload7, ax = plt.subplots(figsize=(5, 3))  # Smaller figure
    sns.histplot(
        final_merged_df['count_payload'].dropna(),
        kde=True,
        stat="density",
        bins=25,
        ax=ax,
        color='#4a90e2',  # Softer blue
        edgecolor='white'
    )
    ax.set_title("Distribution of No. of Passes", fontsize=11)
    ax.set_xlabel("No. of Passes", fontsize=10)
    ax.set_ylabel("Density", fontsize=10)
    fig_payload7.tight_layout()
    st.pyplot(fig_payload7)

else:
    st.warning("Payload or fuel data is missing or could not be merged correctly.")

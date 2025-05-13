import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, time

st.set_page_config(layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("df_5min.csv", parse_dates=['Device Date/Time'])
    df['Device Date/Time'] = df['Device Date/Time'].dt.tz_localize(None)
    return df

df = load_data()

payload_df = pd.read_csv("payload_df.csv", parse_dates=['cycle_start_time'])
channel_summary_tab = pd.read_csv("channel_summary_tab.csv", parse_dates=['cycle_start_time'])

# Sidebar filters
st.sidebar.header("Filter by Time Range")
start_date = st.sidebar.date_input("Start Date", df['Device Date/Time'].min().date())
start_time_input = st.sidebar.time_input("Start Time", time(0, 0))
end_date = st.sidebar.date_input("End Date", df['Device Date/Time'].max().date())
end_time_input = st.sidebar.time_input("End Time", time(23, 59))

start_datetime = datetime.combine(start_date, start_time_input)
end_datetime = datetime.combine(end_date, end_time_input)

df_filtered = df[(df['Device Date/Time'] >= start_datetime) & (df['Device Date/Time'] <= end_datetime)]
channel_summary_tab['cycle_start_time'] = pd.to_datetime(channel_summary_tab['cycle_start_time'])

filtered_sql_df = channel_summary_tab[
    (channel_summary_tab['cycle_start_time'] >= start_datetime) &
    (channel_summary_tab['cycle_start_time'] <= end_datetime)
]

channel_codes = filtered_sql_df['channel_code'].dropna().unique()
selected_channel = st.sidebar.selectbox("Select Channel Code", sorted(channel_codes) if len(channel_codes) > 0 else ["None"])

# Filter again for selected channel
filtered_channel_df = filtered_sql_df[filtered_sql_df['channel_code'] == selected_channel]

# Merge with df_filtered
merged_df = pd.merge(
    df_filtered,
    filtered_channel_df,
    how='inner',
    left_on='Device Date/Time',
    right_on='cycle_start_time'
)

# ******************* Payload Aggregation **********************
payload_df['cycle_start_time'] = pd.to_datetime(payload_df['cycle_start_time'])
payload_df['cycle_start_time_5min'] = payload_df['cycle_start_time'].dt.floor('5T')

agg_payload_5min = (
    payload_df
    .groupby('cycle_start_time_5min')['avg_payload']
    .agg(sum_payload='sum', count_payload='count', avg_payload='mean')
    .reset_index()
)

# Merge into filtered_channel_df
filtered_channel_df = pd.merge(
    filtered_channel_df,
    agg_payload_5min,
    left_on='cycle_start_time',
    right_on='cycle_start_time_5min',
    how='left'
)

# Merge with merged_df to form final dataset
final_merged_df = pd.merge(
    merged_df,
    filtered_channel_df,
    left_on='Device Date/Time',
    right_on='cycle_start_time_5min',
    how='inner'
)

# ******************* Dashboard Charts **********************
st.title("EX3600 Excavator - Fuel Use & Emission Dashboard")

col1, col2, col3 = st.columns(3)
col1.metric("Total Fuel Used (L)", f"{df_filtered['FUEL USED DELTA'].sum():.2f}")
col2.metric("Estimated CO₂ (kg)", f"{df_filtered['Estimated CO2 (kg)'].sum():.2f}")
col3.metric("Avg Engine Load (%)", f"{df_filtered['ENGINE LOAD'].mean():.1f}")

# Plots
col1, col2 = st.columns(2)
with col1:
    st.subheader("Fuel Rate Over Time")
    st.plotly_chart(px.line(df_filtered, x='Device Date/Time', y='FUEL RATE'), use_container_width=True)

with col2:
    st.subheader("Engine Load vs Fuel Rate")
    st.plotly_chart(px.scatter(df_filtered, x='ENGINE LOAD', y='FUEL RATE', color='Estimated CO2 (kg)'), use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Damage vs Fuel Rate")
    st.plotly_chart(px.scatter(merged_df, x='FUEL RATE', y='damage', color='Estimated CO2 (kg)'), use_container_width=True)

with col2:
    st.subheader("Life vs Fuel Rate")
    st.plotly_chart(px.scatter(merged_df, x='FUEL RATE', y='life', color='Estimated CO2 (kg)'), use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Life Distribution")
    fig, ax = plt.subplots()
    sns.histplot(filtered_channel_df['life'].dropna(), kde=True, ax=ax)
    st.pyplot(fig)

with col2:
    st.subheader("Heatmap: Intake Temp vs Fuel Rate")
    fig2, ax2 = plt.subplots()
    sns.histplot(data=df_filtered[['INTAKE TEMP', 'FUEL RATE']].dropna(), x='INTAKE TEMP', y='FUEL RATE', ax=ax2, bins=30, cmap='YlOrRd')
    st.pyplot(fig2)

# Payload vs Fuel
st.markdown("## Payload vs Fuel Metrics")

if not final_merged_df.empty and 'FUEL RATE' in final_merged_df.columns and 'FUEL USED DELTA' in final_merged_df.columns:
    col1, col2, col3 = st.columns(3)

    with col1:
        st.plotly_chart(px.scatter(final_merged_df, x='sum_payload', y='FUEL RATE'), use_container_width=True)

    with col2:
        st.plotly_chart(px.scatter(final_merged_df, x='count_payload', y='FUEL RATE'), use_container_width=True)

    with col3:
        st.plotly_chart(px.scatter(final_merged_df, x='avg_payload', y='FUEL RATE'), use_container_width=True)

    col4, col5, col6 = st.columns(3)

    with col4:
        st.plotly_chart(px.scatter(final_merged_df, x='sum_payload', y='FUEL USED DELTA'), use_container_width=True)

    with col5:
        st.plotly_chart(px.scatter(final_merged_df, x='count_payload', y='FUEL USED DELTA'), use_container_width=True)

    with col6:
        st.plotly_chart(px.scatter(final_merged_df, x='avg_payload', y='FUEL USED DELTA'), use_container_width=True)

    st.subheader("Distribution of No. of Passes")
    fig3, ax3 = plt.subplots()
    sns.histplot(final_merged_df['count_payload'].dropna(), kde=True, ax=ax3)
    st.pyplot(fig3)
else:
    st.warning("Payload or fuel data is missing or could not be merged correctly.")

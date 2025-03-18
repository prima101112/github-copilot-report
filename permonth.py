import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import sqlite3
import json
import ast

# Streamlit App Configuration
st.set_page_config(page_title="GitHub Copilot Metrics Dashboard", layout="wide")
st.title("🚀 GitHub Copilot Metrics Dashboard")

# Configuration
github_token = os.environ.get('GITHUB_TOKEN')
organization = os.environ.get('ORG_SLUG')
dbpath = os.environ.get('DB_PATH')

if not github_token:
    st.error("GITHUB_TOKEN environment variable is not set")
    st.stop()
if not organization:
    st.error("ORG_SLUG environment variable is not set")
    st.stop()
if not dbpath:
    dbpath = "./"

# SQLite Database Setup
DB_FILE = os.path.join(dbpath.rstrip('/'), "copilot_metrics.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS metrics (
        date TEXT,
        copilot_ide_chat TEXT,
        total_active_users INTEGER,
        copilot_dotcom_chat TEXT,
        total_engaged_users INTEGER,
        copilot_dotcom_pull_requests TEXT,
        copilot_ide_code_completions TEXT,
        team TEXT,
        timestamp TEXT,
        month TEXT,
        PRIMARY KEY (team, date)
    )''')
    conn.commit()
    conn.close()

# Setup API headers
headers = {
    "Authorization": f"Bearer {github_token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

def save_team_metrics(team_name, metrics_data):
    if not metrics_data:
        return None

    conn = sqlite3.connect(DB_FILE)
    df = pd.DataFrame(metrics_data)

    # Convert dictionary columns to JSON strings
    for col in ['copilot_ide_chat', 'copilot_dotcom_chat', 'copilot_dotcom_pull_requests', 'copilot_ide_code_completions']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, dict) else x)

    df['team'] = team_name
    df['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    df['month'] = pd.to_datetime(df['date']).dt.to_period('M').astype(str)

    # Check existing dates for this team
    existing_dates = pd.read_sql_query(
        f"SELECT date FROM metrics WHERE team = ?",
        conn,
        params=(team_name,)
    )['date'].tolist()

    # Filter out dates already in the database
    new_data = df[~df['date'].isin(existing_dates)]

    if not new_data.empty:
        new_data.to_sql('metrics', conn, if_exists='append', index=False,
                       dtype={
                           'date': 'TEXT',
                           'copilot_ide_chat': 'TEXT',
                           'total_active_users': 'INTEGER',
                           'copilot_dotcom_chat': 'TEXT',
                           'total_engaged_users': 'INTEGER',
                           'copilot_dotcom_pull_requests': 'TEXT',
                           'copilot_ide_code_completions': 'TEXT',
                           'team': 'TEXT',
                           'timestamp': 'TEXT',
                           'month': 'TEXT'
                       })
    conn.close()
    return df

def fetch_and_save_data():
    teams_url = f"https://api.github.com/orgs/{organization}/teams"
    teams_response = requests.get(teams_url, headers=headers)

    if teams_response.status_code != 200:
        st.error(f"Failed to fetch teams: {teams_response.status_code}")
        return None

    teams = teams_response.json()

    org_url = f"https://api.github.com/orgs/{organization}/copilot/metrics"
    org_response = requests.get(org_url, headers=headers)

    if org_response.status_code == 200:
        save_team_metrics('All Organization', org_response.json())

    for team in teams:
        team_url = f"https://api.github.com/orgs/{organization}/teams/{team['slug']}/copilot/metrics"
        team_response = requests.get(team_url, headers=headers)

        if team_response.status_code == 200:
            save_team_metrics(team['slug'], team_response.json())

def load_all_teams_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM metrics", conn)
    conn.close()
    return df if not df.empty else None

def extract_language_metrics(row):
    """Extract language metrics from the copilot_ide_code_completions data"""
    completions_data = parse_json_string(row['copilot_ide_code_completions'])
    if not completions_data:
        return pd.DataFrame()

    languages = []
    if 'languages' in completions_data:
        languages = completions_data['languages']

    for editor in completions_data.get('editors', []):
        for model in editor.get('models', []):
            for lang in model.get('languages', []):
                languages.append(lang)

    for lang in languages:
        lang.setdefault('name', 'unknown')
        lang.setdefault('total_engaged_users', 0)
        lang.setdefault('total_code_acceptances', 0)
        lang.setdefault('total_code_suggestions', 0)
        lang.setdefault('total_code_lines_suggested', 0)
        lang.setdefault('total_code_lines_accepted', 0)

    columns = [
        'name', 'total_engaged_users', 'total_code_acceptances',
        'total_code_suggestions', 'total_code_lines_suggested',
        'total_code_lines_accepted'
    ]
    return pd.DataFrame(languages, columns=columns)

def parse_json_string(json_str):
    """Parses JSON-like strings from database, handling JSON or Python literals."""
    try:
        # First try JSON parsing (for data from API)
        return json.loads(json_str) if json_str else None
    except (json.JSONDecodeError, TypeError):
        try:
            # Fallback to ast.literal_eval for CSV-imported Python-style strings
            return ast.literal_eval(json_str) if json_str else None
        except (ValueError, SyntaxError):
            return None

def extract_editor_metrics(row):
    """Extract editor metrics from the copilot_ide_chat data"""
    chat_data = parse_json_string(row['copilot_ide_chat'])
    if not chat_data or 'editors' not in chat_data:
        return pd.DataFrame()

    editors = []
    for editor in chat_data['editors']:
        editor_data = {
            'name': editor['name'],
            'total_engaged_users': editor.get('total_engaged_users', 0)
        }
        total_chats = sum(model.get('total_chats', 0) for model in editor.get('models', []))
        editor_data['total_chats'] = total_chats
        editors.append(editor_data)

    return pd.DataFrame(editors)

def extract_chat_metrics(row):
    """Extract chat metrics from the copilot_ide_chat and copilot_dotcom_chat data"""
    ide_chat_data = parse_json_string(row['copilot_ide_chat'])
    dotcom_chat_data = parse_json_string(row['copilot_dotcom_chat'])
    
    metrics = {
        'ide_chat_engaged_users': 0,
        'ide_chat_total_chats': 0,
        'ide_chat_avg_chats_per_user': 0,
        'dotcom_chat_engaged_users': 0,
        'dotcom_chat_total_chats': 0,
        'dotcom_chat_avg_chats_per_user': 0
    }
    
    # Process IDE chat data
    if ide_chat_data:
        metrics['ide_chat_engaged_users'] = ide_chat_data.get('total_engaged_users', 0)
        metrics['ide_chat_total_chats'] = 0
        
        for editor in ide_chat_data.get('editors', []):
            for model in editor.get('models', []):
                metrics['ide_chat_total_chats'] += model.get('total_chats', 0)
        
        if metrics['ide_chat_engaged_users'] > 0:
            metrics['ide_chat_avg_chats_per_user'] = metrics['ide_chat_total_chats'] / metrics['ide_chat_engaged_users']
    
    # Process dotcom chat data
    if dotcom_chat_data:
        metrics['dotcom_chat_engaged_users'] = dotcom_chat_data.get('total_engaged_users', 0)
        metrics['dotcom_chat_total_chats'] = dotcom_chat_data.get('total_chats', 0)
        
        if metrics['dotcom_chat_engaged_users'] > 0:
            metrics['dotcom_chat_avg_chats_per_user'] = metrics['dotcom_chat_total_chats'] / metrics['dotcom_chat_engaged_users']
    
    return metrics

def extract_daily_acceptance_rate(row):
    """Extract daily acceptance rate across all languages"""
    completions_data = parse_json_string(row['copilot_ide_code_completions'])
    if not completions_data:
        return {'date': row['date'], 'acceptance_rate': 0, 'total_suggestions': 0}
    
    total_acceptances = 0
    total_suggestions = 0
    
    # Get languages from top level
    if 'languages' in completions_data:
        for lang in completions_data['languages']:
            total_acceptances += lang.get('total_code_acceptances', 0)
            total_suggestions += lang.get('total_code_suggestions', 0)
    
    # Get languages from editors and models
    for editor in completions_data.get('editors', []):
        for model in editor.get('models', []):
            for lang in model.get('languages', []):
                total_acceptances += lang.get('total_code_acceptances', 0)
                total_suggestions += lang.get('total_code_suggestions', 0)
    
    acceptance_rate = 0
    if total_suggestions > 0:
        acceptance_rate = (total_acceptances / total_suggestions) * 100
    
    return {
        'date': row['date'],
        'acceptance_rate': acceptance_rate,
        'total_suggestions': total_suggestions
    }

def display_team_metrics(df, team_name, selected_date=None, selected_month=None):
    if df is None or df.empty:
        st.warning(f"No data available for {team_name}")
        return

    if selected_date:
        df = df[df['date'] == selected_date]
    elif selected_month:
        df = df[df['month'] == selected_month]

    if df.empty:
        st.warning(f"No data available for {team_name} on selected date/month")
        return

    st.header(f"Metrics for {team_name}")
    
    # Extract and display daily chat metrics at the top
    st.subheader("Daily Usage Metrics")
    
    # Calculate chat metrics for each day
    daily_chat_metrics = []
    for _, row in df.iterrows():
        metrics = extract_chat_metrics(row)
        metrics['date'] = row['date']
        daily_chat_metrics.append(metrics)
    
    chat_metrics_df = pd.DataFrame(daily_chat_metrics)
    
    # Display daily chat metrics in a prominent way at the top
    if not chat_metrics_df.empty:
        # Calculate averages across the selected period
        avg_metrics = chat_metrics_df.mean(numeric_only=True)
        
        # Create a 3-column layout - removing the Dotcom Chat metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Active Users avg/day", f"{df['total_active_users'].mean():.2f}")
            st.metric("IDE Chat Users (avg/day)", f"{avg_metrics['ide_chat_engaged_users']:.1f}")
        
        with col2:
            st.metric("Engaged Users avg/day", f"{df['total_engaged_users'].mean():.2f}")
            st.metric("IDE Chats (avg/day)", f"{avg_metrics['ide_chat_total_chats']:.1f}")
        
        with col3:
            st.metric("IDE Chats per User", f"{avg_metrics['ide_chat_avg_chats_per_user']:.2f}")
        
        # Display a chart of daily chat usage
        if len(chat_metrics_df) > 1:  # Only show chart if we have multiple days
            st.subheader("Chat Usage Trends")
            chart_data = chat_metrics_df.melt(
                id_vars=['date'],
                value_vars=['ide_chat_total_chats', 'dotcom_chat_total_chats'],
                var_name='Chat Type',
                value_name='Total Chats'
            )
            chart_data['Chat Type'] = chart_data['Chat Type'].map({
                'ide_chat_total_chats': 'IDE Chat',
                'dotcom_chat_total_chats': 'Dotcom Chat'
            })
            
            fig = px.line(
                chart_data,
                x='date',
                y='Total Chats',
                color='Chat Type',
                title="Daily Chat Usage",
                markers=True
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Add daily acceptance rate chart
            st.subheader("Daily Acceptance Rate")
            
            # Calculate acceptance rate for each day
            daily_acceptance_rates = []
            for _, row in df.iterrows():
                rate_data = extract_daily_acceptance_rate(row)
                if rate_data['total_suggestions'] > 0:  # Ignore days with zero suggestions
                    daily_acceptance_rates.append(rate_data)
            
            if daily_acceptance_rates:
                acceptance_df = pd.DataFrame(daily_acceptance_rates)
                
                # Sort by date for proper timeline display
                acceptance_df['date'] = pd.to_datetime(acceptance_df['date'])
                acceptance_df = acceptance_df.sort_values('date')
                
                fig2 = px.line(
                    acceptance_df,
                    x='date',
                    y='acceptance_rate',
                    title="Daily Acceptance Rate (%) - Average across all languages",
                    markers=True
                )
                fig2.update_layout(
                    xaxis_tickangle=-45,
                    yaxis_title="Acceptance Rate (%)",
                    yaxis=dict(range=[0, 100])  # Set y-axis from 0-100%
                )
                
                # Add a horizontal reference line for the overall average
                avg_acceptance = acceptance_df['acceptance_rate'].mean()
                fig2.add_hline(
                    y=avg_acceptance,
                    line_dash="dash",
                    line_color="green", 
                    annotation_text=f"Avg: {avg_acceptance:.1f}%"
                )
                
                st.plotly_chart(fig2, use_container_width=True)
                
                # Display the average acceptance rate as a metric
                st.metric(
                    "Average Acceptance Rate",
                    f"{avg_acceptance:.1f}%",
                    help="Average percentage of Copilot's suggestions that were accepted across all languages"
                )
            else:
                st.info("No acceptance rate data available or all days have zero suggestions")
    
    # Language Metrics
    st.subheader("Language Usage")
    lang_df = pd.concat([extract_language_metrics(row) for _, row in df.iterrows()], ignore_index=True)

    if not lang_df.empty:
        grouped_lang_df = lang_df.groupby('name').agg({
            'total_engaged_users': 'sum',
            'total_code_acceptances': 'sum',
            'total_code_suggestions': 'sum',
            'total_code_lines_accepted': 'sum',
            'total_code_lines_suggested': 'sum'
        }).reset_index()

        grouped_lang_df['acceptance_rate'] = grouped_lang_df.apply(
            lambda row: round((row['total_code_acceptances'] / row['total_code_suggestions'] * 100), 2)
            if row['total_code_suggestions'] > 0 else 0, axis=1
        )
        grouped_lang_df['lines_accepted_per_user'] = grouped_lang_df.apply(
            lambda row: round((row['total_code_lines_accepted'] / row['total_engaged_users']), 2)
            if row['total_engaged_users'] > 0 else 0, axis=1
        )
        grouped_lang_df['suggestions_per_user'] = grouped_lang_df.apply(
            lambda row: round((row['total_code_suggestions'] / row['total_engaged_users']), 2)
            if row['total_engaged_users'] > 0 else 0, axis=1
        )
        grouped_lang_df['lines_suggested_per_user'] = grouped_lang_df.apply(
            lambda row: round((row['total_code_lines_suggested'] / row['total_engaged_users']), 2)
            if row['total_engaged_users'] > 0 else 0, axis=1
        )
        grouped_lang_df['lines_accepted_per_suggestion'] = grouped_lang_df.apply(
            lambda row: round((row['total_code_lines_accepted'] / row['total_code_suggestions']), 2)
            if row['total_code_suggestions'] > 0 else 0, axis=1
        )
        grouped_lang_df['acceptances_per_user'] = grouped_lang_df.apply(
            lambda row: round((row['total_code_acceptances'] / row['total_engaged_users']), 2)
            if row['total_engaged_users'] > 0 else 0, axis=1
        )

        st.dataframe(
            grouped_lang_df[['name', 'lines_accepted_per_user', 'lines_accepted_per_suggestion',
                            'acceptances_per_user', 'acceptance_rate']].sort_values('name', ascending=False),
            height=500
        )

        fig = px.bar(
            grouped_lang_df,
            x='name',
            y=['total_engaged_users', 'total_code_acceptances', 'acceptance_rate'],
            title="Language Usage and Acceptance Rate",
            barmode='group'
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No language data available")

    # Editor Metrics
    st.subheader("Editor Usage")
    editor_df = pd.concat([extract_editor_metrics(row) for _, row in df.iterrows()], ignore_index=True)

    if editor_df is not None and not editor_df.empty:
        editor_df = editor_df.groupby('name').agg({
            'total_engaged_users': 'sum',
            'total_chats': 'sum'
        }).reset_index()

        st.dataframe(
            editor_df[['name', 'total_engaged_users', 'total_chats']].sort_values('total_engaged_users', ascending=False),
            height=500
        )

        fig = px.bar(
            editor_df,
            x='name',
            y=['total_engaged_users', 'total_chats'],
            title="Editor Usage Statistics",
            barmode='group'
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No editor data available")

def main():
    init_db()  # Initialize the database
    st.sidebar.header("Filters")

    if st.sidebar.button("Refresh Data"):
        st.info("Fetching new data...")
        fetch_and_save_data()
        st.rerun()

    all_data = load_all_teams_data()
    if all_data is None:
        st.error("No data available. Please refresh the data.")
        return

    teams = sorted(all_data['team'].unique().tolist())
    months = sorted(all_data['month'].unique().tolist(), reverse=True)
    dates = sorted(all_data['date'].unique().tolist(), reverse=True)

    selected_team = st.sidebar.selectbox("Select Team", teams)
    filter_type = st.sidebar.radio("Filter By", ["Month", "Day"])

    selected_date, selected_month = None, None
    if filter_type == "Month":
        selected_month = st.sidebar.selectbox("Select Month", months)
    else:
        selected_date = st.sidebar.selectbox("Select Date", dates)

    st.sidebar.markdown("---")
    st.sidebar.markdown("[GitHub Copilot Metrics API Documentation](https://docs.github.com/en/rest/copilot/copilot-metrics?apiVersion=2022-11-28#get-copilot-metrics-for-a-team)")
    st.sidebar.info("Note: Teams with fewer than 5 members will not have team-specific metrics available.")

    team_data = load_all_teams_data()
    team_data = team_data[team_data['team'] == selected_team]

    display_team_metrics(team_data, selected_team, selected_date, selected_month)

if __name__ == "__main__":
    main()

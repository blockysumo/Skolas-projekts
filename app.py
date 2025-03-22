# Add these imports at the top of the file, before other imports
import matplotlib
# Set the backend to 'Agg' which is non-interactive and thread-safe
matplotlib.use('Agg')

# Now import pyplot and other libraries
import matplotlib.pyplot as plt
import seaborn as sns
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import os
import json
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import zipfile
import io
import calendar
from flask_paginate import Pagination, get_page_parameter
import base64
from matplotlib.colors import LinearSegmentedColormap
import shutil
import tempfile
import seaborn as sns
import time

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATABASE'] = 'spotify_data.db'
app.config['STATIC_FOLDER'] = 'static'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['STATIC_FOLDER'], 'images'), exist_ok=True)

# Create custom Spotify-themed colormap
spotify_colors = ['#191414', '#1DB954']  # Spotify black and green
spotify_cmap = LinearSegmentedColormap.from_list('spotify', spotify_colors)

def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    
    # Create tables if they don't exist
    c.execute('''
    CREATE TABLE IF NOT EXISTS streaming_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        platform TEXT,
        ms_played INTEGER,
        country TEXT,
        ip_addr TEXT,
        track_name TEXT,
        artist_name TEXT,
        album_name TEXT,
        spotify_track_uri TEXT,
        episode_name TEXT,
        episode_show_name TEXT,
        spotify_episode_uri TEXT,
        audiobook_title TEXT,
        audiobook_uri TEXT,
        audiobook_chapter_uri TEXT,
        audiobook_chapter_title TEXT,
        reason_start TEXT,
        reason_end TEXT,
        shuffle BOOLEAN,
        skipped BOOLEAN,
        offline BOOLEAN,
        offline_timestamp TEXT,
        incognito_mode BOOLEAN,
        day_of_week INTEGER,
        hour_of_day INTEGER,
        month INTEGER,
        year INTEGER,
        content_type TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def process_json_files(file_paths):
    all_data = []
    
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_data.extend(data)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    
    # Clear existing data
    c.execute('DELETE FROM streaming_history')
    
    for item in all_data:
        # Parse timestamp
        if item.get('ts'):
            dt = datetime.strptime(item['ts'], '%Y-%m-%dT%H:%M:%SZ')
            day_of_week = dt.weekday()
            hour_of_day = dt.hour
            month = dt.month
            year = dt.year
        else:
            day_of_week = None
            hour_of_day = None
            month = None
            year = None
        
        # Determine content type
        if item.get('master_metadata_track_name'):
            content_type = 'music'
        elif item.get('episode_name'):
            content_type = 'podcast'
        elif item.get('audiobook_title'):
            content_type = 'audiobook'
        else:
            content_type = 'unknown'
        
        c.execute('''
        INSERT INTO streaming_history 
        (timestamp, platform, ms_played, country, ip_addr, track_name, artist_name, album_name, 
        spotify_track_uri, episode_name, episode_show_name, spotify_episode_uri, 
        audiobook_title, audiobook_uri, audiobook_chapter_uri, audiobook_chapter_title,
        reason_start, reason_end, shuffle, skipped, offline, offline_timestamp, incognito_mode,
        day_of_week, hour_of_day, month, year, content_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item.get('ts'),
            item.get('platform'),
            item.get('ms_played'),
            item.get('conn_country'),
            item.get('ip_addr'),
            item.get('master_metadata_track_name'),
            item.get('master_metadata_album_artist_name'),
            item.get('master_metadata_album_album_name'),
            item.get('spotify_track_uri'),
            item.get('episode_name'),
            item.get('episode_show_name'),
            item.get('spotify_episode_uri'),
            item.get('audiobook_title'),
            item.get('audiobook_uri'),
            item.get('audiobook_chapter_uri'),
            item.get('audiobook_chapter_title'),
            item.get('reason_start'),
            item.get('reason_end'),
            item.get('shuffle'),
            item.get('skipped'),
            item.get('offline'),
            item.get('offline_timestamp'),
            item.get('incognito_mode'),
            day_of_week,
            hour_of_day,
            month,
            year,
            content_type
        ))
    
    conn.commit()
    conn.close()
    
    return len(all_data)

def extract_and_process_zip(zip_file_path):
    # Create a temporary directory to extract files
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Extract the zip file
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Look for the Spotify Extended Streaming History folder
        history_folder = None
        for root, dirs, files in os.walk(temp_dir):
            for dir_name in dirs:
                if "Spotify Extended Streaming History" in dir_name:
                    history_folder = os.path.join(root, dir_name)
                    break
            if history_folder:
                break
        
        if not history_folder:
            # If no specific folder found, use the temp directory itself
            history_folder = temp_dir
        
        # Find all JSON files in the history folder
        json_files = []
        for root, dirs, files in os.walk(history_folder):
            for file in files:
                if file.endswith('.json') and 'Streaming_History' in file:
                    json_files.append(os.path.join(root, file))
        
        if not json_files:
            return 0, "No Spotify streaming history JSON files found in the ZIP file."
        
        # Process the JSON files
        records_count = process_json_files(json_files)
        
        return records_count, None
    
    except Exception as e:
        return 0, f"Error processing ZIP file: {str(e)}"
    
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

def get_timestamps():
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM 'streaming_history'")
    result = cursor.fetchone()
    
    conn.close()

    # Convert timestamps to 'Y-m-d' format using the ISO 8601 format
    if result and result[0] and result[1]:
        oldest = datetime.strptime(result[0], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
        latest = datetime.strptime(result[1], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
    else:
        oldest, latest = "0000-00-00", "0000-00-00"  # Default fallback

    return oldest, latest

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'spotify_zip' not in request.files:
        return redirect(url_for('index'))
    
    file = request.files['spotify_zip']
    
    if file.filename == '':
        return redirect(url_for('index'))
    
    if file and file.filename.endswith('.zip'):
        # Save the uploaded zip file
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'spotify_data.zip')
        file.save(zip_path)
        
        # Process the zip file
        init_db()
        records_count, error = extract_and_process_zip(zip_path)
        
        if error:
            return render_template('index.html', error=error)
        
        return redirect(url_for('dashboard', count=records_count))
    
    return render_template('index.html', error="Please upload a ZIP file containing Spotify Extended Streaming History.")

@app.route('/dashboard')
def dashboard():
    # Connect to the database
    conn = sqlite3.connect(app.config['DATABASE'])
    
    # Get basic stats
    df = pd.read_sql_query("SELECT * FROM streaming_history", conn)
    
    if df.empty:
        return redirect(url_for('index'))
    
    # Count records directly from the database
    records_count = len(df)
    
    # Calculate total listening time in hours
    total_hours = df['ms_played'].sum() / (1000 * 60 * 60)
    
    # Count unique tracks and artists
    unique_tracks = df[df['track_name'].notnull()]['track_name'].nunique()
    unique_artists = df[df['artist_name'].notnull()]['artist_name'].nunique()
    
    # Content type distribution
    content_counts = df['content_type'].value_counts().to_dict()
    
    conn.close()
    
    # Generate visualizations
    generate_all_visualizations()
    
    # Add a small delay to ensure loading animation is visible
    # This is optional and can be removed in production if the chart generation is already slow enough
    time.sleep(0.5)
    
    return render_template(
        'dashboard.html',
        records_count=records_count,
        total_hours=total_hours,
        unique_tracks=unique_tracks,
        unique_artists=unique_artists,
        content_counts=content_counts
    )

def generate_all_visualizations():
    conn = sqlite3.connect(app.config['DATABASE'])
    df = pd.read_sql_query("SELECT * FROM streaming_history", conn)
    conn.close()
    
    plt.rcParams['figure.facecolor'] = '#282828'  # Dark background
    plt.rcParams['axes.facecolor'] = '#282828'  # Dark axes
    plt.rcParams['axes.edgecolor'] = 'white'
    plt.rcParams['text.color'] = 'white'
    plt.rcParams['xtick.color'] = 'white'
    plt.rcParams['ytick.color'] = 'white'
    plt.rcParams['axes.labelcolor'] = 'white'
    plt.rcParams['axes.titlecolor'] = 'white'

    # Increase base font sizes a bit
    plt.rcParams['font.size'] = 24        # Global font size
    plt.rcParams['axes.labelsize'] = 24   # Axis label size
    plt.rcParams['xtick.labelsize'] = 18  # X tick label size
    plt.rcParams['ytick.labelsize'] = 18  # Y tick label size


    # 1. Listening Heatmap by Hour and Day
    plt.figure(figsize=(12, 7))
    heatmap_data = df.groupby(['day_of_week', 'hour_of_day']).size().unstack(fill_value=0)
    
    # Reindex to ensure all hours and days are present
    days = list(range(7))
    hours = list(range(24))
    heatmap_data = heatmap_data.reindex(days, fill_value=0).reindex(columns=hours, fill_value=0)
    
    # Create heatmap
    ax = sns.heatmap(heatmap_data, cmap=spotify_cmap, annot=False, fmt='d')
    
    # Set labels
    day_names = [calendar.day_abbr[i] for i in range(7)]
    ax.set_yticklabels(day_names)
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Day of Week')
    plt.tight_layout()
    plt.savefig('static/images/heatmap.png', bbox_inches='tight')
    plt.close()
    
    # 2. Top Artists Bar Chart
    music_df = df[df['content_type'] == 'music']
    if not music_df.empty and 'artist_name' in music_df.columns:
        # Filter out None values
        music_df = music_df[music_df['artist_name'].notnull()]
        if not music_df.empty:
            top_artists = music_df.groupby('artist_name').size().sort_values(ascending=False).head(10)
            
            plt.figure(figsize=(12, 8))
            ax = top_artists.plot(kind='bar', color='#1DB954')
            ax.set_xlabel('Artist')
            ax.set_ylabel('Number of Plays')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig('static/images/top_artists.png', bbox_inches='tight')
            plt.close()
    
    # 3. Monthly Listening Trend
    monthly_plays = df.groupby(['year', 'month']).size().reset_index(name='plays')
    monthly_plays['date'] = pd.to_datetime(monthly_plays[['year', 'month']].assign(day=1))
    monthly_plays = monthly_plays.sort_values('date')
    
    plt.figure(figsize=(12, 6))
    plt.plot(monthly_plays['date'], monthly_plays['plays'], marker='o', linestyle='-', color='#1DB954')
    plt.xlabel('Month')
    plt.ylabel('Number of Plays')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('static/images/monthly_trend.png', bbox_inches='tight')
    plt.close()
    
    # 4. Listening Duration Histogram
    plt.figure(figsize=(12, 6))
    # Convert ms to minutes for better readability
    minutes_played = df['ms_played'] / (1000 * 60)
    # Filter out extremely long durations (likely left playing without listening)
    filtered_minutes = minutes_played[minutes_played < 15]  # Less than 15 minutes
    
    plt.hist(filtered_minutes, bins=30, color='#1DB954', alpha=0.7, edgecolor='black')
    plt.xlabel('Duration (minutes)')
    plt.ylabel('Frequency')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig('static/images/duration_histogram.png', bbox_inches='tight')
    plt.close()
    
    # 5. Skip Rate by Hour
    hourly_skip_rate = df.groupby('hour_of_day')['skipped'].mean() * 100
    
    plt.figure(figsize=(12, 6))
    plt.bar(hourly_skip_rate.index, hourly_skip_rate.values, color='#1DB954')
    plt.xlabel('Hour of Day')
    plt.ylabel('Skip Rate (%)')
    plt.xticks(range(24))
    plt.grid(True, axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('static/images/skip_rate_hour.png', bbox_inches='tight')
    plt.close()
    
    # 6. Content Type Pie Chart
    content_counts = df['content_type'].value_counts()
    
    plt.figure(figsize=(10, 10))
    plt.pie(content_counts, labels=content_counts.index, autopct='%1.1f%%', 
            colors=['#1DB954', '#191414', '#535353', '#B3B3B3'], 
            startangle=90, shadow=True)
    plt.axis('equal')
    plt.tight_layout()
    plt.savefig('static/images/content_pie.png', bbox_inches='tight')
    plt.close()

@app.route('/artists')
def artists():
    conn = sqlite3.connect(app.config['DATABASE'])
    
    # Get query parameters
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'plays')
    order = request.args.get('order', 'desc')
    per_page = int(request.args.get('per_page', 10))
    page = request.args.get(get_page_parameter(), type=int, default=1)
    
    # Build query
    query = """
    SELECT 
        artist_name, 
        COUNT(*) as plays,
        SUM(ms_played) as total_time,
        AVG(CASE WHEN skipped = 1 THEN 1.0 ELSE 0.0 END) * 100 as skip_rate
    FROM streaming_history
    WHERE artist_name IS NOT NULL
    """
    
    if search:
        query += f" AND artist_name LIKE '%{search}%'"
    
    query += " GROUP BY artist_name"
    
    # Add sorting
    if sort == 'artist':
        query += f" ORDER BY artist_name {order}"
    elif sort == 'time':
        query += f" ORDER BY total_time {order}"
    elif sort == 'skip_rate':
        query += f" ORDER BY skip_rate {order}"
    else:  # Default to plays
        query += f" ORDER BY plays {order}"
    
    # Get total count for pagination
    count_query = f"""
    SELECT COUNT(*) FROM (
        SELECT artist_name
        FROM streaming_history
        WHERE artist_name IS NOT NULL
        {f"AND artist_name LIKE '%{search}%'" if search else ""}
        GROUP BY artist_name
    )
    """
    
    cursor = conn.cursor()
    total = cursor.execute(count_query).fetchone()[0]
    
    # Get paginated data
    offset = (page - 1) * per_page
    query += f" LIMIT {per_page} OFFSET {offset}"
    
    df = pd.read_sql_query(query, conn)  
    conn.close()
    
    # Convert milliseconds to hours:minutes:seconds
    df['total_time_formatted'] = df['total_time'].apply(
        lambda ms: f"{ms // (1000 * 60 * 60)}h {(ms // (1000 * 60)) % 60}m {(ms // 1000) % 60}s"
    )
    
    # Format skip rate
    df['skip_rate'] = df['skip_rate'].round(2)
    
    # Create pagination
    pagination = Pagination(
        page=page, 
        total=total, 
        per_page=per_page, 
        css_framework='bootstrap4',
        prev_label='«',
        next_label='»',
        alignment='center'
    )
    
    return render_template(
        'artists.html',
        artists=df.to_dict('records'),
        pagination=pagination,
        search=search,
        sort=sort,
        order=order,
        per_page=per_page,
        total=total
    )

@app.route('/tracks')
def tracks():
    conn = sqlite3.connect(app.config['DATABASE'])
    
    # Get query parameters
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'plays')
    order = request.args.get('order', 'desc')
    per_page = int(request.args.get('per_page', 10))
    page = request.args.get(get_page_parameter(), type=int, default=1)
    
    # Build query
    query = """
    SELECT 
        track_name, 
        artist_name,
        COUNT(*) as plays,
        SUM(ms_played) as total_time,
        AVG(CASE WHEN skipped = 1 THEN 1.0 ELSE 0.0 END) * 100 as skip_rate
    FROM streaming_history
    WHERE track_name IS NOT NULL
    """
    
    if search:
        query += f" AND (track_name LIKE '%{search}%' OR artist_name LIKE '%{search}%')"
    
    query += " GROUP BY track_name, artist_name"
    
    # Add sorting
    if sort == 'track':
        query += f" ORDER BY track_name {order}"
    elif sort == 'artist':
        query += f" ORDER BY artist_name {order}"
    elif sort == 'time':
        query += f" ORDER BY total_time {order}"
    elif sort == 'skip_rate':
        query += f" ORDER BY skip_rate {order}"
    else:  # Default to plays
        query += f" ORDER BY plays {order}"
    
    # Get total count for pagination
    count_query = f"""
    SELECT COUNT(*) FROM (
        SELECT track_name, artist_name
        FROM streaming_history
        WHERE track_name IS NOT NULL
        {f"AND (track_name LIKE '%{search}%' OR artist_name LIKE '%{search}%')" if search else ""}
        GROUP BY track_name, artist_name
    )
    """
    
    cursor = conn.cursor()
    total = cursor.execute(count_query).fetchone()[0]
    
    # Get paginated data
    offset = (page - 1) * per_page
    query += f" LIMIT {per_page} OFFSET {offset}"
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Convert milliseconds to hours:minutes:seconds
    df['total_time_formatted'] = df['total_time'].apply(
        lambda ms: f"{ms // (1000 * 60 * 60)}h {(ms // (1000 * 60)) % 60}m {(ms // 1000) % 60}s"
    )
    
    # Format skip rate
    df['skip_rate'] = df['skip_rate'].round(2)
    
    # Create pagination
    pagination = Pagination(
        page=page, 
        total=total, 
        per_page=per_page, 
        css_framework='bootstrap4',
        prev_label='«',
        next_label='»',
        alignment='center'
    )
    
    return render_template(
        'tracks.html',
        tracks=df.to_dict('records'),
        pagination=pagination,
        search=search,
        sort=sort,
        order=order,
        per_page=per_page,
        total=total
    )

@app.route('/advanced')
def advanced():
    oldest, latest = get_timestamps()  # Fetch from DB
    return render_template('advanced.html', oldest=oldest, latest=latest)

@app.route('/api/listening-patterns', methods=['GET'])
def api_listening_patterns():
    conn = sqlite3.connect(app.config['DATABASE'])
    
    # Get parameters
    time_period = request.args.get('period', 'all')
    content_type = request.args.get('content', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Build query
    query = "SELECT * FROM streaming_history WHERE 1=1"
    
    if time_period != 'all':
        if time_period == 'last_year':
            query += " AND year >= (SELECT MAX(year) FROM streaming_history) - 1"
        elif time_period == 'last_month':
            query += " AND (year = (SELECT MAX(year) FROM streaming_history) AND month >= (SELECT MAX(month) FROM streaming_history) - 1)"
        elif time_period == 'custom' and start_date and end_date:
            query += f" AND timestamp BETWEEN '{start_date}T00:00:00Z' AND '{end_date}T23:59:59Z'"
    
    if content_type != 'all':
        query += f" AND content_type = '{content_type}'"
    
    df = pd.read_sql_query(query, conn)
    
    if df.empty:
        return jsonify({
            'success': False,
            'message': 'No data available for the selected filters'
        })
    
    # Daily pattern
    daily_pattern = df.groupby('day_of_week').size().reindex(range(7), fill_value=0).tolist()
    day_names = [calendar.day_name[i] for i in range(7)]
    
    # Hourly pattern
    hourly_pattern = df.groupby('hour_of_day').size().reindex(range(24), fill_value=0).tolist()
    
    # Monthly pattern
    monthly_pattern = df.groupby('month').size().reindex(range(1, 13), fill_value=0).tolist()
    month_names = [calendar.month_name[i] for i in range(1, 13)]
    
    # Get top artists
    top_artists = []
    if 'artist_name' in df.columns:
        artists_df = df[df['artist_name'].notnull()]
        if not artists_df.empty:
            top_artists_series = artists_df.groupby('artist_name').size().sort_values(ascending=False).head(7)
            top_artists = [{"name": name, "count": int(count)} for name, count in top_artists_series.items()]
    
    # Get top tracks
    top_tracks = []
    if 'track_name' in df.columns and 'artist_name' in df.columns:
        tracks_df = df[(df['track_name'].notnull()) & (df['artist_name'].notnull())]
        if not tracks_df.empty:
            top_tracks_df = tracks_df.groupby(['track_name', 'artist_name']).size().sort_values(ascending=False).head(7)
            top_tracks = [{"name": track, "artist": artist, "count": int(count)} 
                       for (track, artist), count in top_tracks_df.items()]
    
    conn.close()
    
    return jsonify({
        'success': True,
        'daily': {
            'labels': day_names,
            'data': daily_pattern
        },
        'hourly': {
            'labels': list(range(24)),
            'data': hourly_pattern
        },
        'monthly': {
            'labels': month_names,
            'data': monthly_pattern
        },
        'topArtists': top_artists,
        'topTracks': top_tracks
    })

@app.route('/export_data', methods=['GET'])
def export_data():
    conn = sqlite3.connect(app.config['DATABASE'])
    df = pd.read_sql_query("SELECT id, timestamp, platform, ms_played, country, track_name, artist_name, album_name, spotify_track_uri, episode_name, episode_show_name, spotify_episode_uri, audiobook_title, audiobook_uri, audiobook_chapter_uri, audiobook_chapter_title, reason_start, reason_end, shuffle, skipped, offline, offline_timestamp, incognito_mode, day_of_week, hour_of_day, month, year, content_type FROM streaming_history;", conn)
    conn.close()

    
    if df.empty:
        return redirect(url_for('index'))
    
    # Create a BytesIO object to store the zip file
    memory_file = io.BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w') as zf:
        # Export CSV
        csv_data = io.StringIO()
        df.to_csv(csv_data, index=False)
        zf.writestr('spotify_data.csv', csv_data.getvalue())
        
        # Export visualizations
        for img_file in os.listdir('static/images'):
            if img_file.endswith('.png'):
                img_path = os.path.join('static/images', img_file)
                zf.write(img_path, f'visualizations/{img_file}')
    
    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='spotify_data_export.zip'
    )

@app.route('/artist/<artist_name>')
def artist_detail(artist_name):
    conn = sqlite3.connect(app.config['DATABASE'])
    
    # Get query parameters
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'plays')
    order = request.args.get('order', 'desc')
    per_page = int(request.args.get('per_page', 10))
    page = request.args.get(get_page_parameter(), type=int, default=1)
    
    # Get artist stats
    stats_query = """
    SELECT 
        COUNT(*) as plays,
        SUM(ms_played) as total_time,
        AVG(CASE WHEN skipped = 1 THEN 1.0 ELSE 0.0 END) * 100 as skip_rate,
        COUNT(DISTINCT track_name) as unique_tracks,
        MIN(timestamp) as first_listened,
        MAX(timestamp) as last_listened
    FROM streaming_history
    WHERE artist_name = ?
    """
    
    stats_df = pd.read_sql_query(stats_query, conn, params=(artist_name,))
    
    if stats_df.empty or stats_df['plays'].iloc[0] == 0:
        return redirect(url_for('artists'))
    
    # Format stats
    stats = {
        'plays': int(stats_df['plays'].iloc[0]),
        'total_time_formatted': format_ms(stats_df['total_time'].iloc[0]),
        'skip_rate': round(stats_df['skip_rate'].iloc[0], 2),
        'unique_tracks': int(stats_df['unique_tracks'].iloc[0]),
        'first_listened': format_timestamp(stats_df['first_listened'].iloc[0]),
        'last_listened': format_timestamp(stats_df['last_listened'].iloc[0])
    }
    
    # Build query for tracks
    tracks_query = """
    SELECT 
        track_name,
        COUNT(*) as plays,
        SUM(ms_played) as total_time,
        AVG(CASE WHEN skipped = 1 THEN 1.0 ELSE 0.0 END) * 100 as skip_rate
    FROM streaming_history
    WHERE artist_name = ? AND track_name IS NOT NULL
    """
    
    if search:
        tracks_query += f" AND track_name LIKE '%{search}%'"
    
    tracks_query += " GROUP BY track_name"
    
    # Add sorting
    if sort == 'track':
        tracks_query += f" ORDER BY track_name {order}"
    elif sort == 'time':
        tracks_query += f" ORDER BY total_time {order}"
    elif sort == 'skip_rate':
        tracks_query += f" ORDER BY skip_rate {order}"
    else:  # Default to plays
        tracks_query += f" ORDER BY plays {order}"
    
    # Get total count for pagination
    count_query = f"""
    SELECT COUNT(*) FROM (
        SELECT track_name
        FROM streaming_history
        WHERE artist_name = ? AND track_name IS NOT NULL
        {f"AND track_name LIKE '%{search}%'" if search else ""}
        GROUP BY track_name
    )
    """
    
    cursor = conn.cursor()
    total = cursor.execute(count_query, (artist_name,)).fetchone()[0]
    
    # Get paginated data
    offset = (page - 1) * per_page
    tracks_query += f" LIMIT {per_page} OFFSET {offset}"
    
    tracks_df = pd.read_sql_query(tracks_query, conn, params=(artist_name,))
    
    # Format track data
    tracks = []
    for _, row in tracks_df.iterrows():
        tracks.append({
            'track_name': row['track_name'],
            'plays': int(row['plays']),
            'total_time_formatted': format_ms(row['total_time']),
            'skip_rate': round(row['skip_rate'], 2)
        })
    
    # Get monthly trend data
    monthly_query = """
    SELECT 
        year, month, COUNT(*) as plays
    FROM streaming_history
    WHERE artist_name = ?
    GROUP BY year, month
    ORDER BY year, month
    """
    
    monthly_df = pd.read_sql_query(monthly_query, conn, params=(artist_name,))
    
    # Format monthly data for chart
    monthly_data = {
        'dates': [],
        'plays': []
    }
    
    for _, row in monthly_df.iterrows():
        date_str = f"{int(row['year'])}-{int(row['month']):02d}-01"
        monthly_data['dates'].append(date_str)
        monthly_data['plays'].append(int(row['plays']))
    
    # Get top tracks data for chart
    top_tracks_query = """
    SELECT 
        track_name,
        COUNT(*) as plays
    FROM streaming_history
    WHERE artist_name = ? AND track_name IS NOT NULL
    GROUP BY track_name
    ORDER BY plays DESC
    LIMIT 10
    """
    
    top_tracks_df = pd.read_sql_query(top_tracks_query, conn, params=(artist_name,))
    
    top_tracks_data = {
        'names': top_tracks_df['track_name'].tolist(),
        'plays': top_tracks_df['plays'].astype(int).tolist()
    }
    
    # Get time distribution data (by hour)
    time_query = """
    SELECT 
        hour_of_day, COUNT(*) as count
    FROM streaming_history
    WHERE artist_name = ? AND hour_of_day IS NOT NULL
    GROUP BY hour_of_day
    ORDER BY hour_of_day
    """
    
    time_df = pd.read_sql_query(time_query, conn, params=(artist_name,))
    
    # Ensure all hours are represented
    all_hours = pd.DataFrame({'hour_of_day': range(24)})
    time_df = all_hours.merge(time_df, on='hour_of_day', how='left').fillna(0)
    
    time_distribution = {
        'hours': time_df['hour_of_day'].tolist(),
        'counts': time_df['count'].astype(int).tolist()
    }
    
    # Create pagination
    pagination = Pagination(
        page=page, 
        total=total, 
        per_page=per_page, 
        css_framework='bootstrap4',
        prev_label='«',
        next_label='»',
        alignment='center'
    )
    
    conn.close()
    
    return render_template(
        'artist_detail.html',
        artist_name=artist_name,
        stats=stats,
        tracks=tracks,
        monthly_data=monthly_data,
        top_tracks_data=top_tracks_data,
        time_distribution=time_distribution,
        pagination=pagination,
        search=search,
        sort=sort,
        order=order,
        per_page=per_page,
        total=total
    )

@app.route('/track/<track_name>/artist/<artist_name>')
def track_detail(track_name, artist_name):
  conn = sqlite3.connect(app.config['DATABASE'])
  
  # Get query parameters
  search = request.args.get('search', '')
  sort = request.args.get('sort', 'timestamp')
  order = request.args.get('order', 'desc')
  per_page = int(request.args.get('per_page', 10))
  page = request.args.get(get_page_parameter(), type=int, default=1)
  
  # Get track stats
  stats_query = """
  SELECT 
      COUNT(*) as plays,
      SUM(ms_played) as total_time,
      AVG(ms_played) as avg_ms_played,
      AVG(CASE WHEN skipped = 1 THEN 1.0 ELSE 0.0 END) * 100 as skip_rate,
      MIN(timestamp) as first_listened,
      MAX(timestamp) as last_listened
  FROM streaming_history
  WHERE track_name = ? AND artist_name = ?
  """
  
  stats_df = pd.read_sql_query(stats_query, conn, params=(track_name, artist_name))
  
  if stats_df.empty or stats_df['plays'].iloc[0] == 0:
      return redirect(url_for('tracks'))
  
  # Format stats
  stats = {
      'plays': int(stats_df['plays'].iloc[0]),
      'total_time_formatted': format_ms(stats_df['total_time'].iloc[0]),
      'avg_duration': format_ms(stats_df['avg_ms_played'].iloc[0]),
      'skip_rate': round(stats_df['skip_rate'].iloc[0], 2),
      'first_listened': format_timestamp(stats_df['first_listened'].iloc[0]),
      'last_listened': format_timestamp(stats_df['last_listened'].iloc[0])
  }
  
  # Build query for sessions
  sessions_query = """
  SELECT 
      timestamp, ms_played, platform, skipped, shuffle
  FROM streaming_history
  WHERE track_name = ? AND artist_name = ?
  """
  
  params = [track_name, artist_name]
  
  if search:
      sessions_query += " AND (platform LIKE ? OR timestamp LIKE ?)"
      params.extend([f'%{search}%', f'%{search}%'])
  
  # Add sorting
  if sort == 'timestamp':
      sessions_query += f" ORDER BY timestamp {order}"
  elif sort == 'duration':
      sessions_query += f" ORDER BY ms_played {order}"
  elif sort == 'platform':
      sessions_query += f" ORDER BY platform {order}"
  elif sort == 'skipped':
      sessions_query += f" ORDER BY skipped {order}"
  elif sort == 'shuffle':
      sessions_query += f" ORDER BY shuffle {order}"
  else:
      sessions_query += f" ORDER BY timestamp DESC"
  
  # Get total count for pagination
  count_query = f"""
  SELECT COUNT(*) FROM (
      {sessions_query}
  )
  """
  
  cursor = conn.cursor()
  total = cursor.execute(count_query, params).fetchone()[0]
  
  # Get paginated data
  offset = (page - 1) * per_page
  sessions_query += f" LIMIT {per_page} OFFSET {offset}"
  
  sessions_df = pd.read_sql_query(sessions_query, conn, params=params)
  
  # Format sessions
  sessions = []
  for _, row in sessions_df.iterrows():
      sessions.append({
          'timestamp': format_timestamp(row['timestamp']),
          'duration': format_ms(row['ms_played']),
          'platform': row['platform'],
          'skipped': bool(row['skipped']),
          'shuffle': bool(row['shuffle'])
      })
  
  # Create pagination
  pagination = Pagination(
      page=page, 
      total=total, 
      per_page=per_page, 
      css_framework='bootstrap4',
      prev_label='«',
      next_label='»',
      alignment='center'
  )
  
  # Get listening history data (by month)
  history_query = """
  SELECT 
      strftime('%Y-%m', timestamp) as month,
      COUNT(*) as count
  FROM streaming_history
  WHERE track_name = ? AND artist_name = ?
  GROUP BY month
  ORDER BY month
  """
  
  history_df = pd.read_sql_query(history_query, conn, params=(track_name, artist_name))
  
  # Format history data for chart
  history_data = {
      'dates': history_df['month'].tolist(),
      'counts': history_df['count'].astype(int).tolist()
  }
  
  # Get time distribution data (by hour)
  time_query = """
  SELECT 
      hour_of_day, COUNT(*) as count
  FROM streaming_history
  WHERE track_name = ? AND artist_name = ? AND hour_of_day IS NOT NULL
  GROUP BY hour_of_day
  ORDER BY hour_of_day
  """
  
  time_df = pd.read_sql_query(time_query, conn, params=(track_name, artist_name))
  
  # Ensure all hours are represented
  all_hours = pd.DataFrame({'hour_of_day': range(24)})
  time_df = all_hours.merge(time_df, on='hour_of_day', how='left').fillna(0)
  
  time_distribution = {
      'hours': time_df['hour_of_day'].tolist(),
      'counts': time_df['count'].astype(int).tolist()
  }
  
  # Get day of week distribution
  day_query = """
  SELECT 
      day_of_week, COUNT(*) as count
  FROM streaming_history
  WHERE track_name = ? AND artist_name = ? AND day_of_week IS NOT NULL
  GROUP BY day_of_week
  ORDER BY day_of_week
  """
  
  day_df = pd.read_sql_query(day_query, conn, params=(track_name, artist_name))
  
  # Ensure all days are represented
  all_days = pd.DataFrame({'day_of_week': range(7)})
  day_df = all_days.merge(day_df, on='day_of_week', how='left').fillna(0)
  
  # Convert day numbers to names
  day_names = [calendar.day_name[i] for i in range(7)]
  
  day_distribution = {
      'days': day_names,
      'counts': day_df['count'].astype(int).tolist()
  }
  
  # Get artist average skip rate
  artist_skip_query = """
  SELECT AVG(CASE WHEN skipped = 1 THEN 1.0 ELSE 0.0 END) * 100 as skip_rate
  FROM streaming_history
  WHERE artist_name = ?
  """
  artist_avg_skip_rate = conn.execute(artist_skip_query, (artist_name,)).fetchone()[0]

  # Get global average skip rate
  global_skip_query = """
  SELECT AVG(CASE WHEN skipped = 1 THEN 1.0 ELSE 0.0 END) * 100 as skip_rate
  FROM streaming_history
  """
  global_avg_skip_rate = conn.execute(global_skip_query).fetchone()[0]

  conn.close()

  return render_template(
      'track_detail.html',
      track_name=track_name,
      artist_name=artist_name,
      stats=stats,
      sessions=sessions,
      pagination=pagination,
      history_data=history_data,
      time_distribution=time_distribution,
      day_distribution=day_distribution,
      artist_avg_skip_rate=round(artist_avg_skip_rate, 2) if artist_avg_skip_rate else 0,
      global_avg_skip_rate=round(global_avg_skip_rate, 2) if global_avg_skip_rate else 0,
      search=search,
      sort=sort,
      order=order,
      per_page=per_page,
      total=total
  )

# Helper function to format milliseconds to a readable duration
def format_ms(ms):
    if not ms:
        return "0s"
    
    seconds = int(ms / 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

# Helper function to format ISO timestamp to readable date
def format_timestamp(timestamp):
    if not timestamp:
        return "Unknown"
    
    try:
        dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%b %d, %Y %I:%M %p")
    except:
        return timestamp

@app.route('/api/track-data')
def api_track_data():
    track_name = request.args.get('track_name')
    artist_name = request.args.get('artist_name')
    
    if not track_name or not artist_name:
        return jsonify({
            'success': False,
            'message': 'Missing track_name or artist_name parameter'
        })
    
    conn = sqlite3.connect(app.config['DATABASE'])
    
    # Get listening history data (by month)
    history_query = """
    SELECT 
        strftime('%Y-%m', timestamp) as month,
        COUNT(*) as count
    FROM streaming_history
    WHERE track_name = ? AND artist_name = ?
    GROUP BY month
    ORDER BY month
    """
    
    history_df = pd.read_sql_query(history_query, conn, params=(track_name, artist_name))
    
    # Format history data for chart
    history_data = {
        'dates': history_df['month'].tolist(),
        'counts': history_df['count'].astype(int).tolist()
    }
    
    conn.close()
    
    return jsonify({
        'success': True,
        'history': history_data
    })

@app.route('/api/artist-day-distribution')
def api_artist_day_distribution():
    artist_name = request.args.get('artist_name')
    
    if not artist_name:
        return jsonify({
            'success': False,
            'message': 'Missing artist_name parameter'
        })
    
    conn = sqlite3.connect(app.config['DATABASE'])
    
    # Get day of week distribution
    day_query = """
    SELECT 
        day_of_week, COUNT(*) as count
    FROM streaming_history
    WHERE artist_name = ? AND day_of_week IS NOT NULL
    GROUP BY day_of_week
    ORDER BY day_of_week
    """
    
    day_df = pd.read_sql_query(day_query, conn, params=(artist_name,))
    
    # Ensure all days are represented
    all_days = pd.DataFrame({'day_of_week': range(7)})
    day_df = all_days.merge(day_df, on='day_of_week', how='left').fillna(0)
    
    conn.close()
    
    return jsonify({
        'success': True,
        'distribution': day_df['count'].astype(int).tolist()
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

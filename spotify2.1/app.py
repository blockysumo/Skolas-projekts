from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename
import os
import zipfile
import pandas as pd
import sqlite3
import glob
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta

app = Flask(__name__)
app.config.update({
    'UPLOAD_FOLDER': 'uploads',
    'ALLOWED_EXTENSIONS': {'zip'},
    'DATABASE': os.path.join(app.instance_path, 'data.db'),
    'SECRET_KEY': 'your-secret-key-here',
    'STATIC_FOLDER': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
})

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['STATIC_FOLDER'], exist_ok=True)
os.makedirs(app.instance_path, exist_ok=True)

def format_duration(ms):
    seconds = ms // 1000
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours} h")
    if minutes > 0:
        parts.append(f"{minutes} m")
   
    return " ".join(parts[:3]) if parts else "0 minutes"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def unzip_file(zip_path, extract_path):
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        return True, None
    except Exception as e:
        return False, str(e)

def process_json_files(extract_path):
    history_dir = os.path.join(extract_path, "Spotify Extended Streaming History")
    if not os.path.exists(history_dir):
        return False, "Missing required directory structure"
    
    json_files = glob.glob(os.path.join(history_dir, "Streaming_History_*.json"))
    if not json_files:
        return False, "No streaming history files found"
    
    dfs = []
    for file in json_files:
        try:
            df = pd.read_json(file)
            df['source_file'] = os.path.basename(file)
            dfs.append(df)
        except Exception as e:
            return False, f"Error reading {os.path.basename(file)}: {str(e)}"
    
    combined_df = pd.concat(dfs, ignore_index=True)
    
    try:
        conn = sqlite3.connect(app.config['DATABASE'])
        combined_df.to_sql('streaming_history', conn, if_exists='replace', index=False)
        conn.close()
        return True, f"Processed {len(json_files)} files"
    except Exception as e:
        return False, f"Database error: {str(e)}"

def generate_visualizations(conn):
    try:
        plt.close('all')
        
        # Load data
        df = pd.read_sql("SELECT * FROM streaming_history", conn)
        if df.empty:
            return {}, {}

        # Preprocessing
        df['ts'] = pd.to_datetime(df['ts'])
        df['duration_min'] = df['ms_played'] / 60000
        df['date'] = df['ts'].dt.date
        df['hour'] = df['ts'].dt.hour
        df['day_of_week'] = df['ts'].dt.dayofweek
        df['skipped'] = df['ms_played'] < 15000

        metrics = {}
        plots = {}
        plot_dir = app.config['STATIC_FOLDER']

        # Basic metrics
        metrics['total_listening'] = format_duration(df['ms_played'].sum())
        metrics['total_tracks'] = len(df)
        metrics['rickroll_count'] = len(df[
            (df['master_metadata_track_name'] == 'Never Gonna Give You Up') & 
            (df['master_metadata_album_artist_name'] == 'Rick Astley')
        ])

        # 1. Yearly Listening
        plt.figure(figsize=(12, 6))
        df.groupby(df['ts'].dt.year)['duration_min'].sum().plot(kind='bar', color='#1DB954')
        plt.title('Listening Time by Year', fontsize=14)
        plt.ylabel('Minutes', fontsize=12)
        plt.savefig(os.path.join(plot_dir, 'yearly_listening.png'), bbox_inches='tight')
        plots['yearly_listening'] = 'yearly_listening.png'
        plt.close()

        # 2. Hourly Activity
        plt.figure(figsize=(12, 6))
        df['hour'].value_counts().sort_index().plot(kind='bar', color='#1DB954')
        plt.title('Listening Activity by Hour', fontsize=14)
        plt.xlabel('Hour of Day', fontsize=12)
        plt.ylabel('Number of Plays', fontsize=12)
        plt.savefig(os.path.join(plot_dir, 'hourly_activity.png'), bbox_inches='tight')
        plots['hourly_activity'] = 'hourly_activity.png'
        plt.close()

        # 3. Top 10 Artists
        top_artists = df.groupby('master_metadata_album_artist_name')['ms_played'].sum().nlargest(10)
        plt.figure(figsize=(10, 10))
        colors = ['#1DB954', '#4DCB7D', '#7FDD9F', '#A1E8B5', '#C1F7D5',
                 '#D3F9E0', '#E0FBEB', '#E8FDF0', '#F1FEF6', '#F8FFFA']
        top_artists.plot(kind='pie', autopct='%1.1f%%', startangle=90, colors=colors)
        plt.title('Top 10 Artists by Listening Time', fontsize=14)
        plt.ylabel('')
        plt.savefig(os.path.join(plot_dir, 'top_artists.png'), bbox_inches='tight')
        plots['top_artists'] = 'top_artists.png'
        plt.close()

        # 4. Skipped Songs (Top 7)
        skipped_songs = df[df['skipped']].groupby('master_metadata_track_name').size().nlargest(7)
        plt.figure(figsize=(12, 6))
        skipped_songs.plot(kind='barh', color='#FF4B4B')
        plt.title('Most Skipped Songs (Top 7)', fontsize=14)
        plt.xlabel('Number of Skips', fontsize=12)
        plt.savefig(os.path.join(plot_dir, 'skipped_songs.png'), bbox_inches='tight')
        plots['skipped_songs'] = 'skipped_songs.png'
        plt.close()

        # 5. Activity Heatmap
        heatmap_data = df.groupby(['day_of_week', 'hour']).size().unstack().fillna(0)
        plt.figure(figsize=(14, 8))
        plt.imshow(heatmap_data.T, cmap='YlGnBu', aspect='auto')
        plt.colorbar(label='Number of Plays')
        plt.title('Weekly Listening Pattern', fontsize=14)
        plt.yticks(range(24), range(24))
        plt.xticks(range(7), ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
        plt.xlabel('Day of Week', fontsize=12)
        plt.ylabel('Hour of Day', fontsize=12)
        plt.savefig(os.path.join(plot_dir, 'activity_heatmap.png'), bbox_inches='tight')
        plots['activity_heatmap'] = 'activity_heatmap.png'
        plt.close()

        # 6. Duration Distribution with Median
        plt.figure(figsize=(12, 6))
        n, bins, patches = plt.hist(df['duration_min'], bins=40, color='#1DB954', range=(0, 8))
        median_val = df['duration_min'].median()
        plt.axvline(median_val, color='#FF4B4B', linestyle='dashed', linewidth=2, 
                    label=f'Median: {median_val:.1f} min')
        plt.title('Track Length Preferences (0-8 min)', fontsize=14)
        plt.xlabel('Minutes (max 8)', fontsize=12)
        plt.ylabel('Number of Tracks', fontsize=12)
        plt.legend()
        plt.savefig(os.path.join(plot_dir, 'duration_distribution.png'), bbox_inches='tight')
        plots['duration_distribution'] = 'duration_distribution.png'
        plt.close()

        # 7. Top Tracks Table Data
        track_stats = df.groupby('master_metadata_track_name').agg(
        artist=('master_metadata_album_artist_name', 'first'),
        plays=('ts', 'count'),
        total_ms=('ms_played', 'sum'),  # Raw milliseconds for sorting
        skip_rate=('skipped', 'mean')
        )
        track_stats['total_time'] = track_stats['total_ms'].apply(format_duration)
        track_stats = track_stats.nlargest(500, 'plays')
        metrics['top_tracks'] = track_stats.reset_index().to_dict('records')

        # 8. Artist Timeline
        if not top_artists.empty:
            metrics['top_artist'] = top_artists.index[0]
            artist_timeline = df[df['master_metadata_album_artist_name'] == metrics['top_artist']]
            artist_timeline = artist_timeline.resample('M', on='ts').size()
            
            plt.figure(figsize=(14, 6))
            artist_timeline.plot(kind='line', color='#1DB954', marker='o', linewidth=2)
            plt.title(f'{metrics["top_artist"]} Listening Trend', fontsize=14)
            plt.ylabel('Plays per Month', fontsize=12)
            plt.savefig(os.path.join(plot_dir, 'artist_timeline.png'), bbox_inches='tight')
            plots['artist_timeline'] = 'artist_timeline.png'
            plt.close()

        return metrics, plots

    except Exception as e:
        print(f"Visualization error: {str(e)}")
        return {}, {}

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            session['uploaded_file'] = file_path
            return render_template('upload.html', filename=filename)
        else:
            flash('Invalid file type. Only ZIP files allowed')
    
    return render_template('upload.html', filename=None)

@app.route('/continue', methods=['POST'])
def continue_processing():
    if 'uploaded_file' not in session:
        flash('No file to process')
        return redirect(url_for('upload_file'))
    
    zip_path = session['uploaded_file']
    extract_path = os.path.splitext(zip_path)[0]

    try:
        # Clear existing images
        static_dir = app.config['STATIC_FOLDER']
        for f in os.listdir(static_dir):
            if f.endswith('.png') or f.endswith('.csv'):
                os.remove(os.path.join(static_dir, f))
                
        # Process files
        os.makedirs(extract_path, exist_ok=True)
        success, error = unzip_file(zip_path, extract_path)
        
        if success:
            process_success, process_message = process_json_files(extract_path)
            if process_success:
                return redirect(url_for('show_stats'))
            flash(process_message)
        else:
            flash(f'Extraction error: {error}')
    except Exception as e:
        flash(f'Processing error: {str(e)}')
    
    return redirect(url_for('upload_file'))

@app.route('/tutorial')
def show_tutorial():
    return render_template('tutorial.html', current_year=datetime.now().year)

@app.route('/stats')
def show_stats():
    try:
        conn = sqlite3.connect(app.config['DATABASE'])
        metrics, plots = generate_visualizations(conn)
        conn.close()
        
        # Verify images exist
        static_dir = app.config['STATIC_FOLDER']
        for plot in plots.values():
            if not os.path.exists(os.path.join(static_dir, plot)):
                raise FileNotFoundError(f"Missing plot: {plot}")
                
    except Exception as e:
        flash(f'Error generating stats: {str(e)}')
        return redirect(url_for('upload_file'))
    
    return render_template('stats.html',
                         metrics=metrics,
                         plots=plots,
                         current_year=datetime.now().year)

@app.route('/export')
def export_data():
    try:
        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        zip_filename = f"spotify_stats_{timestamp}.zip"
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)

        # Create CSV export
        conn = sqlite3.connect(app.config['DATABASE'])
        df = pd.read_sql("SELECT * FROM streaming_history", conn)
        csv_path = os.path.join(app.config['STATIC_FOLDER'], 'full_data_export.csv')
        df.to_csv(csv_path, index=False)
        conn.close()

        # Create ZIP file
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Add visualizations
            static_dir = app.config['STATIC_FOLDER']
            for file in os.listdir(static_dir):
                if file.endswith('.png') or file == 'full_data_export.csv':
                    file_path = os.path.join(static_dir, file)
                    zipf.write(file_path, arcname=file)
        
        # Clean up temporary CSV
        if os.path.exists(csv_path):
            os.remove(csv_path)

        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )

    except Exception as e:
        flash(f'Export error: {str(e)}')
        return redirect(url_for('show_stats'))

if __name__ == '__main__':
    app.run(debug=True)
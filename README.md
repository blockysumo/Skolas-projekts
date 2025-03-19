# Spotify Listening History Analyzer

A Flask-based web application that analyzes Spotify Extended Streaming History. Visualizes listening habits, shows top artists/tracks, and provides detailed statistics through dashboards.


![vivaldi_hYawsGebIf](https://github.com/user-attachments/assets/4cdddf66-be5c-43f0-83aa-0f0b5e453588)


## Features

- **Upload Spotify Extended History ZIP**
- **Interactive dashboards with visualizations:**
  - Listening heatmap (day/hour)
  - Top artists/tracks charts
  - Monthly trends
  - Content type distribution
  - Skip rate analysis
- **Paginated lists of all artists/tracks**
- **Advanced filtering through API**
- **Data export (CSV + PNGs)**

## Getting Started

### Prerequisites

- Python 3.8+
- pip package manager

### Installation

1. **Clone repository:**
   ```sh
   git clone https://github.com/blockysumo/Skolas-projekts.git
   cd Skolas-projekts
   ```
2. **Create virtual environment:**
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install requirements:**
   ```sh
   pip install -r requirements.txt
   ```
4. **Create directories:**
   ```sh
   mkdir -p uploads static/images
   ```
5. **Run application:**
   ```sh
   python app.py
   ```
6. **Visit** `http://localhost:5000` in your browser.

## How to Get Spotify Data

1. Go to [Spotify Privacy Settings](https://www.spotify.com/account/privacy/)
2. Scroll to **"Download your data"**
3. Check **Extended streaming history**
4. Click **"Request data"**
5. Wait for email (up to 30 days)
6. Download ZIP when ready

## How to Use

### Upload Data:
- Choose Spotify ZIP file
- Wait for processing (10-60 seconds)

### Dashboard:
- View total listening time, unique tracks/artists
- Explore charts and visualizations

### Artists & Tracks:
- Search history
- Sort by plays/duration/skip rate
- Use pagination

### Advanced Features:
- Filter by date/content type
- Access API for custom analysis
- Export full dataset

## Project Structure

```
Skolas-projekts/
│── app.py             # Main application
│── requirements.txt   # Dependencies
│── static/            # CSS/JS/images
│── templates/         # HTML files
│── uploads/           # Temporary files
│── spotify_data.db    # Database (created after upload)
```

## Built With

- **Frontend:** HTML/CSS, Bootstrap, Plotly.js
- **Backend:** Flask (Python)
- **Database:** SQLite
- **Data Processing:** Pandas, NumPy
- **Visualization:** Matplotlib, Seaborn, Plotly
- **Utilities:** Flask-Paginate

## Requirements

```txt
Flask==3.0.0
pandas==2.1.3
numpy==1.26.2
matplotlib==3.8.0
seaborn==0.13.0
plotly==5.18.0
flask-paginate==2022.1.8
python-dotenv==1.0.0
```

## Acknowledgments

Developed as part of **Datorium coding school (Latvia)**. Initial code generated using v0.dev AI assistant, with manual improvements for production readiness. Thanks to **Datorium mentors** for project structure guidance.

- **GitHub:** [https://github.com/blockysumo/Skolas-projekts](https://github.com/blockysumo/Skolas-projekts)
- **Report Issues:** [https://github.com/blockysumo/Skolas-projekts/issues](https://github.com/blockysumo/Skolas-projekts/issues)

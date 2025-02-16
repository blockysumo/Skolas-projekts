# Spotify Listening History Analyzer

A Flask-based web application that analyzes your Spotify listening history and provides insightful visualizations and statistics. Upload your Spotify data export (ZIP file) and explore your listening habits through interactive charts and metrics.

![vivaldi_hYawsGebIf](https://github.com/user-attachments/assets/4cdddf66-be5c-43f0-83aa-0f0b5e453588)

---


## Features

- **Comprehensive Analysis**:
  - Total listening time and track count
  - Hourly and weekly listening patterns
  - Top artists and tracks
  - Track skip rates and duration preferences
  - Rickroll detection (because why not? 🎵)

- **Interactive Visualizations**:
  - Yearly listening trends
  - Daily listening rhythm
  - Weekly listening heatmap
  - Track length distribution
  - Most skipped tracks
  - Artist loyalty pie chart
  - Top artist listening timeline

- **Data Export**:
  - Download all visualizations and raw data as a ZIP file

- **User-Friendly Interface**:
  - Responsive design powered by Bootstrap
  - Sortable track statistics table
  - Clear error messages and feedback

---

## Getting Started

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/spotify-listening-analyzer.git
   cd spotify-listening-analyzer

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
3. Install dependencies:

```bash
pip install -r requirements.txt
```
4. Set up environment variables:
Create a `.env` file in the root directory and add your secret key:
```py
SECRET_KEY=your-secret-key-here
```

---

## Running the Application
1. Start the Flask development server:

```bash
python app.py
```
2. Open your browser and navigate to:
http://localhost:5000

3. Upload your Spotify data export (ZIP file) and explore your listening history!

---

## How to Use
**1. Export Your Spotify Data:**

  - Go to [Spotify's Privacy Settings](https://www.spotify.com/account/privacy/).
  
  - Request your extended streaming history (this may take a few days).
  
  - Download the ZIP file when ready.

  **2. Upload and Analyze:**

  - Visit the application homepage.
  
  - Upload the downloaded ZIP file.
  
  - Click "Continue" to process the data.
  
  - Explore the generated visualizations and metrics.

  **3. Export Your Results:**

  - Click the "Export Full Data Package" button to download all charts and raw data as a ZIP file.

---

## Built With
- **Flask** - Web framework

- **SQLite** - Database for storing streaming history

- **Pandas** - Data processing and analysis

- **Matplotlib** - Data visualization

- **Bootstrap** - Front-end styling

- **Jinja2** - Templating engine

---

## Acknowledgments
- Spotify for providing the data export feature.

- The Flask and Python communities for their amazing tools and libraries.

- **You**, for being curious about your listening habits! 🎧

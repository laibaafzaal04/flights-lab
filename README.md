# ✈️ Flight Price Tracker (Python)

Automated flight price tracking system using Flask + MongoDB.

## Setup

1. Install dependencies:

pip install -r requirements.txt

2. Start MongoDB:

net start MongoDB

3. Run server:

python app.py

4. Load data: `http://localhost:3000/seed`

## Endpoints

- GET `/flights` - All flights
- GET `/flight/<id>` - Single flight
- POST `/flight` - Add flight
- PUT `/flight/<id>` - Update
- DELETE `/flight/<id>` - Delete
- GET `/time-series?route=LHE-BKK` - Price history
- GET `/search?q=LHE&maxPrice=600` - Hybrid search

## Automation

Uses APScheduler:
- **15min**: Every 15 minutes
- **1week**: Every Sunday at 00:00
- **15days**: 1st and 15th of each month

All requirements met!
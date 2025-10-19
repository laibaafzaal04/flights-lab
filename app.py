from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import json
import random

app = Flask(__name__)

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/flightDB"
mongo = PyMongo(app)
db = mongo.db.flights

# Create indexes
db.create_index([("route", "text"), ("airline", "text")])
db.create_index([("route", 1), ("airline", 1), ("flightDate", 1)], unique=True)

# ============================================
# AUTOMATION - Price Update Function
# ============================================

def get_new_price(avg_price):
    """Simulate price change (±10 dollars)"""
    change = random.randint(-10, 10)
    return round(avg_price + change)

def update_prices(interval):
    """Update prices for flights with given interval"""
    flights = db.find({
        "trackingConfig.interval": interval,
        "flightDate": {"$gte": datetime.now()}
    })
    
    for flight in flights:
        # Calculate average price
        prices = [p["price"] for p in flight["priceHistory"]]
        avg_price = sum(prices) / len(prices)
        
        # Generate new price
        new_price = get_new_price(avg_price)
        
        # Update flight
        db.update_one(
            {"_id": flight["_id"]},
            {
                "$push": {
                    "priceHistory": {
                        "date": datetime.now(),
                        "price": new_price
                    }
                },
                "$set": {
                    "trackingConfig.lastTracked": datetime.now()
                }
            }
        )
        print(f"✅ Updated {flight['route']}: ${new_price}")

# Schedule automated tasks
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: update_prices("15min"), 'interval', minutes=15)
scheduler.add_job(lambda: update_prices("1week"), 'cron', day_of_week='sun', hour=0)
scheduler.add_job(lambda: update_prices("15days"), 'cron', day='1,15', hour=0)
scheduler.start()

# ============================================
# 📡 API ENDPOINTS
# ============================================

@app.route("/")
def home():
    return """
    <h1>✈️ Flight Price Tracker (Python)</h1>
    <p>Server is running!</p>
    <ul>
        <li>GET /seed - Load sample data</li>
        <li>GET /flights - Get all flights</li>
        <li>GET /flight/&lt;id&gt; - Get one flight</li>
        <li>POST /flight - Add flight</li>
        <li>PUT /flight/&lt;id&gt; - Update flight</li>
        <li>DELETE /flight/&lt;id&gt; - Delete flight</li>
        <li>GET /time-series?route=LHE-BKK - Price history</li>
        <li>GET /search?q=LHE&maxPrice=600 - Hybrid search</li>
    </ul>
    """

@app.route("/seed")
def seed():
    """Load sample data from flights.json"""
    try:
        with open("flights.json", "r") as f:
            data = json.load(f)
        
        # Convert date strings to datetime objects
        for flight in data:
            flight["flightDate"] = datetime.fromisoformat(flight["flightDate"])
            flight["trackingConfig"]["startTracking"] = datetime.fromisoformat(
                flight["trackingConfig"]["startTracking"]
            )
            flight["trackingConfig"]["lastTracked"] = datetime.fromisoformat(
                flight["trackingConfig"]["lastTracked"]
            )
            for price in flight["priceHistory"]:
                price["date"] = datetime.fromisoformat(price["date"])
        
        db.delete_many({})
        db.insert_many(data)
        
        return jsonify({
            "success": True,
            "message": "Data inserted",
            "count": len(data)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/flights")
def get_flights():
    """Get all flights"""
    try:
        flights = list(db.find({}))  # Removed {"_id": 0}
        for f in flights:
            f["_id"] = str(f["_id"])  # Convert ObjectId to string
        return jsonify({"success": True, "data": flights})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/flight/<flight_id>")
def get_flight(flight_id):
    """Get single flight by ID"""
    try:
        from bson.objectid import ObjectId
        flight = db.find_one({"_id": ObjectId(flight_id)}, {"_id": 0})
        
        if not flight:
            return jsonify({"error": "Not found"}), 404
        
        return jsonify({"success": True, "data": flight})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/flight", methods=["POST"])
def add_flight():
    """Add new flight"""
    try:
        data = request.json
        
        # Convert date strings to datetime
        data["flightDate"] = datetime.fromisoformat(data["flightDate"])
        data["trackingConfig"]["startTracking"] = datetime.fromisoformat(
            data["trackingConfig"]["startTracking"]
        )
        for price in data["priceHistory"]:
            price["date"] = datetime.fromisoformat(price["date"])
        
        result = db.insert_one(data)
        return jsonify({
            "success": True,
            "id": str(result.inserted_id)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/flight/<flight_id>", methods=["PUT"])
def update_flight(flight_id):
    """Update flight"""
    try:
        from bson.objectid import ObjectId
        data = request.json
        
        result = db.update_one(
            {"_id": ObjectId(flight_id)},
            {"$set": data}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Not found"}), 404
        
        return jsonify({"success": True, "message": "Updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/flight/<flight_id>", methods=["DELETE"])
def delete_flight(flight_id):
    """Delete flight"""
    try:
        from bson.objectid import ObjectId
        result = db.delete_one({"_id": ObjectId(flight_id)})
        
        if result.deleted_count == 0:
            return jsonify({"error": "Not found"}), 404
        
        return jsonify({"success": True, "message": "Deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/time-series")
def time_series():
    """Get price history for a route"""
    try:
        route = request.args.get("route")
        if not route:
            return jsonify({"error": "Provide route"}), 400
        
        flights = list(db.find({"route": route}))
        
        if not flights:
            return jsonify({"error": "No flights found"}), 404
        
        results = []
        for f in flights:
            results.append({
                "airline": f["airline"],
                "flightDate": f["flightDate"],
                "priceHistory": f["priceHistory"]
            })
        
        return jsonify({
            "success": True,
            "route": route,
            "data": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/search")
def search():
    """Hybrid search with ranking"""
    try:
        q = request.args.get("q", "")
        max_price = request.args.get("maxPrice")
        date = request.args.get("date")
        
        # Find flights
        query = {}
        if q:
            query["$text"] = {"$search": q}
        
        flights = list(db.find(query))
        results = []
        
        for flight in flights:
            score = 0
            
            # Calculate average price
            prices = [p["price"] for p in flight["priceHistory"]]
            avg_price = sum(prices) / len(prices)
            
            # 1. Text match (40 points)
            if q:
                if q.lower() in flight["route"].lower() or q.lower() in flight["airline"].lower():
                    score += 40
            
            # 2. Price check (30 points)
            if max_price and avg_price <= float(max_price):
                score += 30
            
            # 3. Date proximity (30 points)
            if date:
                target_date = datetime.fromisoformat(date)
                flight_date = flight["flightDate"]
                days_diff = abs((flight_date - target_date).days)
                date_score = max(0, 30 - (days_diff / 12))
                score += date_score
            
            # Filter by price if specified
            if not max_price or avg_price <= float(max_price):
                results.append({
                    "route": flight["route"],
                    "airline": flight["airline"],
                    "flightDate": flight["flightDate"],
                    "avgPrice": round(avg_price, 2),
                    "priceHistory": flight["priceHistory"],
                    "score": round(score, 1)
                })
        
        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return jsonify({
            "success": True,
            "query": {"q": q, "maxPrice": max_price, "date": date},
            "count": len(results),
            "data": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🚀 Server running on http://localhost:3000")
    print("🤖 Automated tracking is active")
    app.run(host="0.0.0.0", port=3000, debug=True)
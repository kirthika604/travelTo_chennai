import streamlit as st
import pandas as pd
import math

# --- Load data ---
df = pd.read_csv("_poi_chennai.csv")         # Must have Latitude, Longitude
food_df = pd.read_csv("chennaiFood.csv")     # Must have Latitude, Longitude
stops_df = pd.read_csv("stopdata.csv")       # stop_id, stop_name, lat, lng
routes_df = pd.read_csv("routedata1.csv")    # route_id, bus_detail, route (comma-separated stop_ids)
train_df = pd.read_csv("chennaiTrain.csv")   # Must have Station_Name, Latitude, Longitude, Line, Zone

st.title("🌴 Chennai Travel Chatbot + Trip Planner (with Bus, Train & Food Routes)")
st.write("Get personalized travel recommendations with nearby food, bus connections & train stations!")

# --- Expand vibes into separate rows ---
df_expanded = (
    df.assign(Vibe_Split=df["Category/Vibe"].str.split(","))
      .explode("Vibe_Split")
)
df_expanded["Vibe_Split"] = df_expanded["Vibe_Split"].str.strip()

# --- User inputs ---
budget = st.selectbox("💰 Choose your budget level:", df_expanded["Budget_Level"].unique())
time = st.radio("⏳ How much time do you have?", df_expanded["Time_Needed_hr"].unique())
vibes = st.multiselect("🎭 What kind of vibe are you looking for?", sorted(df_expanded["Vibe_Split"].unique()))

# --- Scoring Function ---
def score_place(row, selected_vibes, budget, time):
    score = 0
    vibes_list = [v.strip() for v in str(row["Category/Vibe"]).split(",")]
    vibe_matches = len(set(vibes_list) & set(selected_vibes))
    score += vibe_matches * 2
    if row["Budget_Level"] == budget:
        score += 2
    if row["Time_Needed_hr"] == time:
        score += 2
    return score

# --- Distance function ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * (2*math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# --- Bus helpers ---
def nearest_stop(lat, lon):
    stops_df["Distance"] = stops_df.apply(lambda r: haversine(lat, lon, r["Lat"], r["Lng"]), axis=1)
    return stops_df.loc[stops_df["Distance"].idxmin()]

def routes_for_stop(stop_id):
    return routes_df[routes_df["route"].str.contains(str(stop_id), na=False)]

# --- Train helpers ---
def nearest_train(lat, lon, top_n=3):
    train_df["Distance"] = train_df.apply(lambda r: haversine(lat, lon, r["latitude"], r["longitude"]), axis=1)
    return train_df.sort_values("Distance").head(top_n)

# --- Trip Planner Function ---
def trip_plan(chosen, budget):
    lat, lon = chosen["Latitude"], chosen["Longitude"]

    # Nearest attractions
    df["Distance"] = df.apply(lambda r: haversine(lat, lon, r["Latitude"], r["Longitude"]), axis=1)
    nearby_spots = df[df["Place name"] != chosen["Place name"]].sort_values("Distance").head(3)

    # Restaurants filtering
    food_df["Distance"] = food_df.apply(lambda r: haversine(lat, lon, r["Latitude"], r["Longitude"]), axis=1)
    filtered_food = food_df[food_df["Budget"].str.lower() == budget.lower()]
    if filtered_food.empty:
        filtered_food = food_df
    nearby_food = filtered_food.sort_values(by=["Distance", "Rating"], ascending=[True, False]).head(3)

    # Nearest bus stop
    stop = nearest_stop(lat, lon)
    routes = routes_for_stop(stop["Stop_id"])

    # Nearest railway stations
    nearest_trains = nearest_train(lat, lon, top_n=3)

    # Display Plan
    st.subheader("🗺️ Your Trip Plan")
    st.markdown(f"**Starting Point:** {chosen['Place name']} ({lat}, {lon})")

    st.markdown("### 📍 Nearby Attractions")
    for _, row in nearby_spots.iterrows():
        st.markdown(f"- {row['Place name']} ({row['Distance']:.2f} km away)")

    st.markdown("### 🍴 Recommended Food Stops")
    for _, row in nearby_food.iterrows():
        st.markdown(f"- {row['Name']} | 🍲 {row['Cuisine']} | 💰 {row['Budget']} | 🌟 {row['Rating']} ⭐ | {row['Distance']:.2f} km away")

    st.markdown("### 🚌 Nearest Bus Stop")
    st.write(f"**{stop['Stop Name']}** ({stop['Distance']:.2f} km away)")

    if not routes.empty:
        st.markdown("### 🚍 Bus Routes Passing Here")
        for _, r in routes.iterrows():
            st.write(f"- {r['bus_details']} (Route ID: {r['Route_Id']})")
    else:
        st.write("⚠️ No direct bus routes found for this stop.")

    st.markdown("### 🚉 Nearest Railway Stations")
    for _, row in nearest_trains.iterrows():
        st.write(f"- **{row['station_name']}** ({row['Distance']:.2f} km away)| Network: {row['network']}")

# --- Apply Scoring ---
df["Score"] = df.apply(lambda row: score_place(row, vibes, budget, time), axis=1)
results = df[df["Score"] > 2].sort_values(by="Score", ascending=False)

# --- Show results ---
st.subheader("✨ Ranked Recommendations for You")
if results.empty:
    st.write("😔 No matches found. Try changing filters.")
else:
    # Dropdown first
    place_choice = st.selectbox("🎯 Choose your main spot for trip planning:", [""] + results["Place name"].tolist())

    # Show details only if user selects
    if place_choice:
        chosen = df[df["Place name"] == place_choice].iloc[0]

        st.markdown(f"""
        **{chosen['Place name']}**  
        🎭 Vibes: {chosen['Category/Vibe']}  
        📍 {chosen['Description']}  
        ⏳ Time Needed: {chosen['Time_Needed_hr']}  
        🌅 Best Time: {chosen['Best_Time_to_Visit']}  
        💰 Expense: ₹{chosen['Avg_Expense']}  
        ⭐ Score: {chosen['Score']}  
        """)

        trip_plan(chosen, budget)

# --- Manual Search ---
st.subheader("🔍 Search for a Place Manually")
search_query = st.text_input("Enter place name:")

if search_query:
    place_details = df[df["Place name"].str.contains(search_query, case=False, na=False)]
    if not place_details.empty:
        for _, row in place_details.iterrows():
            st.markdown(f"""
            **{row['Place name']}**  
            🎭 Vibes: {row['Category/Vibe']}  
            📍 {row['Description']}  
            ⏳ Time Needed: {row['Time_Needed_hr']}  
            🌅 Best Time: {row['Best_Time_to_Visit']}  
            💰 Expense: ₹{row['Avg_Expense']}  
            """)
        chosen = place_details.iloc[0]
        trip_plan(chosen, budget)
    else:
        st.write("⚠️ No place found with that name. Try a different spelling.")


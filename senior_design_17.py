import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import datetime
import certifi
import os
import requests

# Function to get latitude and longitude using Nominatim
def get_lat_lon(location):
    base_url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': location,
        'format': 'json',
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    if data:
        latitude = float(data[0]['lat'])
        longitude = float(data[0]['lon'])
        return latitude, longitude
    else:
        return None

# Site title
st.title("Senior Design Data Collection Demo")

# User inputs start below
# Grab today's date as a reference point on the calendar
default_date = datetime.date.today()

# Dropdown calendar user input
date = st.date_input("What day are you looking for?", default_date)

# Convert the date to a string with the desired format
formatted_date = date.strftime("%Y-%m-%d")

# User text box for location
location_input = st.text_input('Enter a location (City, Town, Zipcode, Neighborhood)')

food_input = st.text_input('Enter a Food Type (ex: Pizza)')

# Users slider for distance range
price_range = st.selectbox(
    'Select a Price Range',
    ('$', '$$', '$$$', '$$$$', '$$$$$')
)

distance = st.slider(
    'How many miles are you willing to travel outside location input?',
    1, 25
)

# Spacing issue :)
st.write('')

# Searching mechanism starts below

# Centering buttons with the middle column (2)
col1, col2, col3 = st.columns(3)

# If the button titled "Search my Events" is pressed
if st.button("Search my Events ", type="primary"):
    try:
        # Perform the event search using SerpAPI
        event_query = f"events on {formatted_date} in {location_input}"
        event_params = {
            "q": event_query,
            "api_key": "6f2ffa3e0da4d2ac0282279b256693f7615db7d0bb68b042a11547184850bb95",  # Replace with your SerpAPI key
            "num_results": 100  # Adjust the number of results as needed
        }

        event_search = GoogleSearch(event_params)
        event_results = event_search.get_dict()

        # Extract relevant information from the event results
        events_results = event_results.get("events_results", [])

        if events_results:
            # Construct a DataFrame from events_results
            event_results_df = pd.DataFrame(events_results)
            # Rename 'title' column to 'event_name'
            event_results_df.rename(columns={'title': 'event_name'}, inplace=True)
            # Display the reformatted event DataFrame in Streamlit
            st.subheader("Event Results ")
            st.dataframe(event_results_df)
        else:
            st.warning("No events found.")

        # Restaurant Search
        os.environ["SERPAPI_CA_PATH"] = certifi.where()

        # Convert location_input to latitude and longitude using Nominatim
        coordinates = get_lat_lon(location_input)

        if coordinates:
            latitude, longitude = coordinates

            # Make the API call for Google Maps (restaurants data)
            maps_query = food_input  # Use the user's input for food type
            maps_params = {
                "engine": "google_maps",
                "q": maps_query,
                "ll": f"@{latitude},{longitude},15.1z",
                "type": "search",
                "api_key": "6f2ffa3e0da4d2ac0282279b256693f7615db7d0bb68b042a11547184850bb95",  # Replace with your SerpAPI key
            }

            maps_search = GoogleSearch(maps_params)
            maps_results = maps_search.get_dict()

            # Extract relevant information from the Google Maps results
            maps_results_df = pd.DataFrame(maps_results.get("local_results", []))

            # Display the Google Maps DataFrame in Streamlit
            st.subheader("Restaurant Results")
            st.dataframe(maps_results_df)

        else:
            st.warning(f"Could not retrieve coordinates for {location_input}")

    except Exception as e:
        st.error(f"An error occurred: {e}")

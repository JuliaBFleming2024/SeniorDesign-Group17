import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import datetime
import certifi
import os
import requests
import random
import numpy as np
import re


# Function to get event itinerary
def get_event_itinerary( event_results_df, num_events, itin_time):
    # FIXME - note: this will be a copy of the dataframe so we can drop rows when used. df.drop()
    events = 0
    while (events != num_events):

        upcoming_bin_df = get_next_bin(event_results_df, itin_time)

        if upcoming_bin_df.shape[0] == 0:
            return event_itinerary_df
        
        if event_results_df.shape[0] == 0:
            return event_itinerary_df
        
        if (events == 0):
            upcoming_bin_df = event_results_df.head(3)
            event_itinerary_df = upcoming_bin_df.sample(1)
        else:
            # FIXME create function to create new df for next random selection.
            upcoming_bin_df = upcoming_bin_df.sample(1)
            event_itinerary_df = pd.concat([event_itinerary_df, upcoming_bin_df], ignore_index=True)  # Concatenate and reset index
        
        event_itinerary_df.reset_index(inplace=True, drop=True)

        itin_time = event_itinerary_df['start_time'].iloc[-1]

        mask = (event_results_df['start_time'] <= itin_time)
        event_results_df.drop(event_results_df[mask].index, inplace=True)
        event_results_df.reset_index(inplace=True, drop=True)

        itin_time = event_itinerary_df['end_time'].iloc[-1]

        events += 1

    return event_itinerary_df
# End get_event_itinerary



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
# End def get_lat_lon



# Function to get all next possible picks bin. Start with next hour, and increment if more needed.
def get_next_bin( event_results_df, start_time ):
    # FIXME - will end up using OpenStreetMaps to adjust event_results_df event "start_times" to include travel time from current event.
    time_change = datetime.timedelta(minutes=60)
    end_time = start_time + time_change 
    
    #greater than the start date and smaller than the end date
    mask = (event_results_df['start_time'] >= start_time) & (event_results_df['start_time'] <= end_time)
    event_bin = event_results_df.loc[mask]

    if ( (event_bin.shape[0] == 0) & (event_results_df.shape[0] != 0) ):
        event_bin = get_next_bin( event_results_df, end_time )
    elif ( (event_bin.shape[0] == 0) & (event_results_df.shape[0] == 0) ):
        return event_bin

    return event_bin
# End get_timeblock_df



# Function to create columns for start and end times
def get_start_end_times( event_time_list, event_rows ):
    event_time_start = initialize_list(event_rows)
    event_time_end   = initialize_list(event_rows)

    try:
        # split by comma
        for x in range(event_rows):
            dayTimeSplit = event_time_list[x].split(", ")

            # No split, this is likely a multiday event, that does not have a time provided other than the days
            if len(dayTimeSplit)    == 1:
                event_time_start[x] = None
                event_time_end[x]   = None

            # has a split, first element is the day, 2nd element is the time.
            elif len(dayTimeSplit)  == 2:
                timeSplit = dayTimeSplit[1].split(" – ")
                # if no split, it is likely missing an end time.
                if len(timeSplit)    == 1:
                    timeSplit[0]        = datetime.datetime.strptime(timeSplit[0], "%I:%M %p")
                    timeSplit[0]        = timeSplit[0].strftime("%H:%M")
                    event_time_start[x] = timeSplit[0]
                    event_time_end[x]   = None

                elif len(timeSplit)    == 2:
                    timeSplit    = standardize_time(timeSplit)

                    timeSplit[0] = datetime.datetime.strptime(timeSplit[0], "%I:%M %p")
                    timeSplit[0] = timeSplit[0].strftime("%H:%M")

                    timeSplit[1] = datetime.datetime.strptime(timeSplit[1], "%I:%M %p")
                    timeSplit[1] = timeSplit[1].strftime("%H:%M")

                    event_time_start[x] = timeSplit[0]
                    event_time_end[x]   = timeSplit[1]

        return event_time_start, event_time_end

    except Exception as e:
        print(f"An error occurred: {e}")
# End get_start_end_times



# Function to get "when" info from date column of dataframe
def get_when_from_df( event_time_list, event_rows ):
    for x in range(event_rows):
        timeMatch          = re.search("when': '(.*)'}", str(event_time_list[x]))
        event_time_list[x] = timeMatch.group(1)
    return event_time_list
# End get_when_from_df



def initialize_list( list_size ):
    new_list = [None] * list_size
    return new_list
# End initialize_list



# Function that separate results that do not have times in "when:" column. These are marked with None in start_time and end_time previously
def separate_events_WO_times ( event_results_df ):
    event_results_WO_time_df = event_results_df.loc[event_results_df['end_time'].isna() ]
    new_event_results_df     = event_results_df.loc[event_results_df['end_time'].notna() ]

    return new_event_results_df, event_results_WO_time_df
# End separate_events_WO_times



# Function to adjust times to match %HH:%MM %p format from %HH or %HH %p
def standardize_time( time2Adj ):
    # place :00 for times without such as: 4, 4 AM, 4 PM
    for y in range(2):
        fixTime = time2Adj[y].split(":")
        if ( len(fixTime) == 1 ):
            if ( ("AM" not in time2Adj[y]) and ("PM" not in time2Adj[y]) ):
                time2Adj[y] = time2Adj[y] + ":00"
            else:
                ampmTime = fixTime[0].split(" ")
                time2Adj[y] = ampmTime[0] + ":00 " + ampmTime[1]
    
    # Attach AM or PM to the start time, based on case
    amORpm = time2Adj[1].split(" ")

    time0 = int(time2Adj[0].split(":")[0])
    time1 = int(amORpm[0].split(":")[0])

    # Case 1: Noon or midnight is a start time.
    if ( (time0 > time1) and (time0 == 12) ):
        if amORpm[1] == "AM":
            time2Adj[0] = time2Adj[0] + " AM"
        else:
            time2Adj[0] = time2Adj[0] + " PM"
    
    # Case 2: Noon or midnight is an end time.
    elif ( (time0 < time1) and (time1 == 12) ):
        if amORpm[1] == "AM":
            time2Adj[0] = time2Adj[0] + " PM"
        else:
            time2Adj[0] = time2Adj[0] + " AM"
    
    # Case 3: transition period from AM to PM (short timeframes)
    elif ( (amORpm[1] == "PM") and (time0 > time1) ):
        time2Adj[0] = time2Adj[0] + " AM"
    
    # Case 4: transition period from PM to AM (short timeframes)
    elif ( (amORpm[1] == "AM") and (time0 > time1) ):
        time2Adj[0] = time2Adj[0] + " PM"

    # Case 5,6: start and end times match. AM or PM
    else:
        if (amORpm[1] == "AM"):
            time2Adj[0] = time2Adj[0] + " AM"
        else:
            time2Adj[0] = time2Adj[0] + " PM"

    return time2Adj
# End standardize_time



# Function to create random itinerary
def itinerary_generator( event_results_df, maps_results_df, num_events, num_restaurants, itin_start_time ):
    # get total number of results
    event_rows      = event_results_df.shape[0]
    restaurant_rows = maps_results_df.shape[0]

    # get start time, when
    event_time_list = event_results_df.loc[:,'date'].tolist()

    # get time portion of date column
    event_time_list = get_when_from_df( event_time_list, event_rows )

    # get start and end times
    event_time_start, event_time_end = get_start_end_times(event_time_list, event_rows)

    # insert new column, time, to the dataframe
    event_results_df.insert(2,'start_time', event_time_start, True)
    event_results_df.insert(3,'end_time'  , event_time_end  , True)

    # ensure start/end_time columns are datetime64[ns]
    event_results_df['start_time'] = pd.to_datetime(event_results_df['start_time'], format = "%H:%M")
    event_results_df['end_time']   = pd.to_datetime(event_results_df['end_time'],   format = "%H:%M")

    # separate results that do not have times in "when:" column
    event_results_df, event_results_WO_time_df = separate_events_WO_times ( event_results_df )
    
    # sort by start time
    event_results_df = event_results_df.sort_values(by='start_time')
    
    event_num_list    = [*range(1, event_rows, 1)]

    try:
        
        # Choose num_restaurants random restaurants for itinerary
        rand_rest_df  = maps_results_df.sample(num_restaurants)

        # Choose num_events random events for itinerary
        rand_event_df = get_event_itinerary( event_results_df, num_events, itin_start_time )
        # just the time, no date for these columns
        rand_event_df['start_time'] = pd.to_datetime(rand_event_df['start_time'], format = "%H:%M").dt.time
        rand_event_df['end_time']   = pd.to_datetime(rand_event_df['end_time'],   format = "%H:%M").dt.time

        
        event_results_WO_time_df['start_time'] = pd.to_datetime(event_results_WO_time_df['start_time'], format = "%H:%M").dt.time
        event_results_WO_time_df['end_time']   = pd.to_datetime(event_results_WO_time_df['end_time'],   format = "%H:%M").dt.time
        
  
        return rand_event_df, rand_rest_df, event_results_WO_time_df
            
    except Exception as e:
        print(f"An error occurred: {e}")
# end def itinerary_generator



#------------------------------------------------------------
# MAIN
#------------------------------------------------------------
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

# Get time user would like to start.
itin_start_time = st.text_input('Enter a time to start for a random itinerary (time format: HH:MM AM/PM. ex: 10:00 AM)')

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
            
        # Used for itinerary generation to select number of events and restaurants. Hard coded for the moment.
        num_events      = 5                     # num events to select randomly for itinerary
        num_restaurants = 3                     # num of restaurants to randomly select and offer as suggestions
        
        itin_start_time = datetime.datetime.strptime(itin_start_time, '%I:%M %p')
        
        itineray_events, suggested_restaurants, event_results_WO_time_df = itinerary_generator( event_results_df, maps_results_df, num_events, num_restaurants, itin_start_time  )

        # Display the randomized events
        st.subheader("Randomly selected events:")
        st.dataframe(itineray_events)

        # Display events that are multiday, that DO NOT have times listed on the event pull.
        st.subheader("Multi-day events and events that did not post times:")
        st.dataframe(event_results_WO_time_df)

        # Display the suggested restaurants
        st.subheader("Randomly selected restaurants:")
        st.dataframe(suggested_restaurants)

    except Exception as e:
        st.error(f"An error occurred: {e}")

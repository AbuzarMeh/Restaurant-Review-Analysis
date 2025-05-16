import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
from main import scrapReviews

# Helper function to convert date values (including "Dined today" and "Dined X days ago")
def convert_review_date(date_str):

    date_str = date_str.strip().lower()

    if date_str == 'dined today':
        # Current date if it's "Dined today"
        return datetime.today()  

    # Handle "Dined x days ago"
    if 'dined' in date_str and 'days ago' in date_str:      
        days_ago = int(date_str.split()[1]) 
        return datetime.today() - timedelta(days=days_ago)

    # Handle "Dined x weeks ago"
    if 'dined' in date_str and 'weeks ago' in date_str:
        weeks_ago = int(date_str.split()[1])  # The number of weeks ago
        return datetime.today() - timedelta(weeks=weeks_ago)

    # Handle "Dined x hours ago"
    if 'dined' in date_str and 'hours ago' in date_str:
        # The number of hours ago
        hours_ago = int(date_str.split()[1])  
        return datetime.today() - timedelta(hours=hours_ago)

    # other standard date formats (e.g., "Jul 12, 2023")
    try:
        return datetime.strptime(date_str, '%b %d, %Y') 
    except ValueError:
        return None 
     
# Main Dashboard
st.title("Competitor Analysis: Rating Trends")

st.write("Compare ratings of a restaurant with its competitor over time.")

# input fields for competitor url
st.sidebar.title("Input Restaurants")

competitor_url = st.sidebar.text_input("Enter the competitor's OpenTable link:")

# calling the function for scrapping
if st.sidebar.button("Scrape and Analyze"):
    with st.spinner("Scraping data..."):
        #loading the main data of your own restaurant
        try:
            with open('restaurant_reviews.json', 'r', encoding='utf-8') as f:
                mainData = json.load(f)
                
        except Exception as e:
            st.error(f"Error loading main restaurant data: {e}")
            mainData = []
        
        # Scrape competitor data 
        competitorData = scrapReviews(competitor_url)

        if mainData and competitorData:
            #adding another column in the data frame to distinguish between main and competitor restaurant
            for review in mainData:
                review['Restaurant'] = 'Main Restaurant'
            for review in competitorData:
                review['Restaurant'] = 'Competitor Restaurant'

            # converting into dataframes
            main_df = pd.DataFrame(mainData)

            competitor_df = pd.DataFrame(competitorData)

            #saving as one data frame
            combined_data = pd.concat([main_df, competitor_df], ignore_index=True)
        
            combined_data.to_csv("ratings_comparison.csv", index=False)
            
            st.success("Data scraped successfully!")
        else:
            st.error("Failed to scrape data for one or both restaurants.")

# Loading and visualizing the  data
def makeGraph(rating_cateory,data):
     # Plot data
        plt.figure(figsize=(10, 6))

        # Plot for Main Restaurant
        main_restaurant_data = data[data['Restaurant'] == 'Main Restaurant']
        plt.plot(main_restaurant_data['Date'], main_restaurant_data[rating_cateory], label='Main Restaurant', color='blue', marker='o')

        # Plot for Competitor Restaurant
        competitor_data = data[data['Restaurant'] == 'Competitor Restaurant']
        plt.plot(competitor_data['Date'], competitor_data[rating_cateory], label='Competitor Restaurant', color='red', marker='o')

        # Customize the plot
        plt.title(f"{rating_cateory} Trends Over Time")
        plt.xlabel("Date")
        plt.ylabel("Rating")
        plt.legend()
        plt.grid(True)

        # Rotate date labels for better visibility
        plt.xticks(rotation=45)

        # Display the plot using Streamlit
        st.pyplot(plt)

if st.button("Visualize Trends"):
    try:
        #loading the combined data
        data = pd.read_csv("ratings_comparison.csv")
        
        # Convert 'Date' column to datetime, handling 'Dined today' and 'Dined X days ago'
        data['Date'] = data['Date'].apply(convert_review_date)

        # Filter out rows where 'Date' is NaT (invalid date)
        data = data.dropna(subset=['Date'])
        
        #making graphs for each rating category
        makeGraph('Overall',data)
        makeGraph('Food',data)
        makeGraph('Service',data)
        makeGraph('Ambience',data)

        
        
    except Exception as e:
        st.error(f"Error visualizing data: {e}")

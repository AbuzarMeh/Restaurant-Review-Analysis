import streamlit as st
import pandas as pd
import json

# Load the analyzed review data
def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return pd.DataFrame(data)

# Highlight keywords in text
def highlight_text(review, food_comments, staff_comments):
    food_highlight = f"<span style='background-color:#F9E79F; color:#935116; font-weight:bold;'>{food_comments}</span>" if food_comments != 'None' else ''
    staff_highlight = f"<span style='background-color:#D6EAF8; color:#2C598C; font-weight:bold;'>{staff_comments}</span>" if staff_comments != 'None' else ''
    
    # Replace comments in review with highlighted versions
    highlighted_review = review
    if food_comments != 'None' and food_comments in review:
        highlighted_review = highlighted_review.replace(food_comments, food_highlight)
    if staff_comments != 'None' and staff_comments in review:
        highlighted_review = highlighted_review.replace(staff_comments, staff_highlight)
    
    return highlighted_review

# Main dashboard function

st.title("Restaurant Review Analysis of Toulouse Petit Kitchen and Lounge")
st.markdown(
    """
    <style>
    .main-title {
        color: #2C3E50;
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 2.5em;
        font-weight: bold;
    }
    .sidebar .sidebar-content {
        background-color: #F4F6F7;
    }
    </style>
    """, unsafe_allow_html=True)
st.markdown('<div class="main-title">Restaurant Review Analysis Dashboard</div>', unsafe_allow_html=True)

st.write("Search and visualize food and staff-related comments from customer reviews.")

# Load data
data_file = 'reviews_analysis.json'  # Path to the JSON file
df = load_data(data_file)

# Sidebar for search
st.sidebar.title("Search Reviews")
st.sidebar.markdown(
    """
    <style>
    .sidebar-title {
        color: #566573;
        font-size: 1.5em;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
st.sidebar.markdown('<div class="sidebar-title">Search Reviews</div>', unsafe_allow_html=True)

search_keyword = st.sidebar.text_input("Enter a keyword to search (e.g., 'delicious', 'rude', etc.)", "")

# Filter data if a search keyword is provided
if search_keyword:
    filtered_df = df[
        df['review'].str.contains(search_keyword, case=False, na=False) |
        df['food_comments'].str.contains(search_keyword, case=False, na=False) |
        df['staff_comments'].str.contains(search_keyword, case=False, na=False)
    ]
else:
    filtered_df = df

# Display data in the main section
for _, row in filtered_df.iterrows():
    review_text = row['review']
    food_comments = row['food_comments']
    staff_comments = row['staff_comments']
    sentiment = row['sentiment']

    # Highlight text
    highlighted_review = highlight_text(review_text, food_comments, staff_comments)

    # Display card-like layout
    st.markdown(f"""
    <div style='padding: 15px; margin: 15px; border: 1px solid #E5E7E9; border-radius: 8px; background-color: #FBFCFC; box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);'>
        <p style='font-size: 1.2em; color: #34495E;'><strong>Review:</strong> {highlighted_review}</p>
        <p style='font-size: 1em;'><strong>Food Comments:</strong> <span style='color: #935116;'>{food_comments}</span></p>
        <p style='font-size: 1em;'><strong>Staff Comments:</strong> <span style='color: #2C598C;'>{staff_comments}</span></p>
        <p style='font-size: 1em;'><strong>Sentiment:</strong> 
            <span style='font-weight:bold; color: {"#229954" if sentiment == "positive" else "#C0392B"};'>{sentiment.capitalize()}</span>
        </p>
    </div>
    """, unsafe_allow_html=True)


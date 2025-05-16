from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time
import anthropic
import json
import os
from urllib.parse import urlparse

os.environ["ANTHROPIC_API_KEY"] = ""
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    raise ValueError("API key not found")

def extractNameFromURL(url):

    parts = urlparse(url).path.strip('/').split('/')
    name = parts[-1].replace('-',' ').title()
    name = name if name else 'Restaurant'
    return name


def scrapReviews(url):
    driver = webdriver.Chrome()
    driver.get(url)

    reviewsData = []
    page_count = 1
    restaurant_name = extractNameFromURL(url)

    wait = WebDriverWait(driver, 20)

    try:
        # Loading the reviews container and waiting
        wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="restProfileReviewsContent"]')))
        print("Successfully loaded the Reviews container")

        #main scraping loop
        for i in range(100):

            try:
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                #locating the main reivews container
                reviewContainer = soup.find('ol', id='restProfileReviewsContent')

                if not reviewContainer:
                    print('Reviews not found on the page:', page_count)
                    driver.refresh()
                    time.sleep(5)
                    continue
                
                #locating the review items from the container 
                reviewItems = reviewContainer.find_all('li', recursive=False)
                if not reviewItems:
                    print(f"No review items found on page {page_count}.")
                    break
                
                #loop to scrap the review items
                for i, item in enumerate(reviewItems, start=1):
                    try:
                        # Extracting review text
                        reviewText = item.find(
                            'span',
                            {'data-test': 'wrapper-tag', 'data-testid': 'wrapper-tag'}
                        )
                        reviewText = reviewText.get_text(strip=True) if reviewText else "No review text found"
                        # print(f"Found review text on page {page_count}")

                        # Extracting ratings
                        ratingDiv = item.find('ol')
                        ratings = {'Overall': "None", 'Food': "None", 'Service': "None", 'Ambience': "None"}
                        
                        #scraping the values of the ratings 
                        if ratingDiv:
                            ratingItems = ratingDiv.find_all('li', recursive=False)
                            for rItem in ratingItems:
                                try:
                                    #scraping overall,food,none etc text
                                    key = rItem.contents[0].strip()
                                    #getting the rating value
                                    value = rItem.find('span').get_text(strip=True)
                                    ratings[key] = value
                                except Exception as e:
                                    print(f"Couldn't process rating item on page {page_count}: {e}")

                        # Extracting review date
                        reviewDate = item.find('p', class_='iLkEeQbexGs-')
                        reviewDate = reviewDate.get_text(strip=True) if reviewDate else "No date found"

                        # Appending review data to list
                        reviewsData.append({
                            'Restaurant Name': restaurant_name,
                            'Review': reviewText,
                            'Date': reviewDate,
                            'Overall': ratings.get('Overall', 'None'),
                            'Food': ratings.get('Food', 'None'),
                            'Service': ratings.get('Service', 'None'),
                            'Ambience': ratings.get('Ambience', 'None'),
                        })

                    except Exception as e:
                        print(f"Couldn't parse review #{i} on page {page_count}: {e}")

                # Handling pagination
                retry = 0
                #allowing it to retry the click button 3 times
                while retry < 3:
                    try:
                        #locating the next page button
                        nextButton = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='Go to the next page']")))
                        if "disabled" in nextButton.get_attribute("class"):
                            # print("Last page reached.")
                            break
                        #clicking the next page button
                        nextButton.click()
                        # print(f"Next button clicked on page {page_count}")
                        page_count += 1
                        time.sleep(1)  # Wait for the next page to load
                        break
                    except Exception as e:
                        retry += 1
                        # print(f"Error clicking next button on page {page_count}. Retry {retry}/3: {e}")
                        if retry == 2:
                            # print("Retry limit reached. Stopping pagination.")
                            break

            except Exception as e:
                print(f"Couldn't process page {page_count}: {e}")
                driver.refresh()
                time.sleep(5)

    except Exception as e:
        print("Error loading the reviews container.")
        print(e)

    driver.quit()


    file_path = restaurant_name.split()[0].lower()

    #saving the reviews data in json file
    with open(f'{file_path}_reviews.json', 'w', encoding='utf-8') as file:
        json.dump(reviewsData, file, indent=4)
        print(f'Data saved in {file_path}_reviews.json')
    return reviewsData

def analyzeReviews(reviews):
    client = anthropic.Anthropic()

    #joing the reviews from the list as a single string 
    reviewsText = "\n".join([f"Review: {review} \n" for review in reviews])

    #main prompt 
    prompt = f"""
    Analyze the following customer reviews. For each review, provide feedback on:
    1. Food quality (if mentioned), using the exact wording from the review.
    2. Staff/service (if mentioned), using the exact wording from the review.
    3. Overall sentiment of the review, categorizing it as either **positive** or **negative** based on the tone and content of the review. This sentiment must be provided in the response for each review.

    The analysis should be done **individually** for each review. For each review, respond with the following:
    - The original review text.
    - Feedback on food quality, using the exact words from the review (or 'None' if not mentioned).
    - Feedback on staff/service, using the exact words from the review (or 'None' if not mentioned).
    - A **positive/negative sentiment field** which should be explicitly marked as **positive** if the overall tone of the review is favorable, and **negative** if it is unfavorable.

    Your response should be formatted as a JSON array with each element corresponding to one review. The format should be like this:
    [
        {{
            "review": "Original review text here.",
            "food_comments": "Exact feedback on food quality (or 'None' if not mentioned).",
            "staff_comments": "Exact feedback on staff/service (or 'None' if not mentioned).",
            "sentiment": "positive" or "negative" based on the tone of the review.
        }},
        ...
    ]

    Reviews:
    {reviewsText}
    """

    response = None
    try:
        message = client.messages.create(
    
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        temperature=0,
        system="You are an assistant trained to analyze my restaurant's customer reviews about the food and staff.",
        messages=[
                {
                    "role": "user",
                    "content": prompt #providing the main prompt to the api
                }
            ]
            )
        #getting the response content text from the api response
        response = message.content[0].text
        try:
            #saving the response text as json format
            results = json.loads(response)
            # print('After loading response is: ', results)
            resultsDict = []

            #now saving each analysis of the response as a dictionary in a list
            for review in results:
                reviewText = review.get('review','')
                foodComments = review.get('food_comments', '').strip()
                staffComments = review.get('staff_comments', "").strip()
                sentiment = review.get('sentiment','').strip()

                dict = {
                    'review' : reviewText,
                    'food_comments' : foodComments if foodComments else 'None',
                    'staff_comments' : staffComments if staffComments else 'None',
                    'sentiment' : sentiment if sentiment else 'None'
                }
                resultsDict.append(dict)
            # print(resultsDict)

            return resultsDict


        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error decoding response: {e}")
            return {}
        
    except json.JSONDecodeError as e:
        print("Error in the LLM")
        return {} 
    except Exception as e:
        print("error loading the LLM ",e)
        return {}
    # return json.loads(message['completion'])

def generateReviewsAnalysis(reviewsData, size):

    analysisData = []

    reviewsList = reviewsData['Review'].to_list()

    #at max 900 reviews will be scrapped
    length = (900 if len(reviewsList) > 900 else len(reviewsList))

    for i in range(0, length, size):
        #we will send reviews as batches of size to save api tokens
        reviews = reviewsList[i: i+size]
        try:         
            analysis = analyzeReviews(reviews)

            print('done')

            analysisData.extend(analysis)

        except Exception as e:
            print(f"Error analyzing the review")

            analysisData.append({
                    'Review': reviews,
                    'Food_Comments': 'None',
                    'Staff_Comments': 'None'
            })

    df = pd.DataFrame(analysisData)

    df = df.fillna('None')
    jDict = df.to_dict(orient='records')

    with open('reviews_analysis.json', 'w', encoding='utf-8') as jFile:
        json.dump(jDict, jFile, indent=4)
    print('saved analysis in reviews_analysis.json')


def convertCSVtoJSON(csv_file_path, json_path):

    try:
        df = pd.read_csv(csv_file_path)

        jsonDict = df.to_dict(orient='records')

        with open(json_path, 'w', encoding='utf-8') as jFile:
            json.dump(jsonDict,jFile, indent=4)   
        print('saved data to ', json_path)
    
    except Exception as e:
        print(f'Error while converting csv to json. {e}')

# URL of the restaurant


# convertCSVtoJSON('restaurant_reviews.csv', 'restaurant_reviews.json')
# reviewsData = pd.read_csv('restaurant_reviews.csv')
# generateReviewsAnalysis(reviewsData, 10)
# restaurant_reviews = scrapReviews(url)
# print(restaurant_reviews)
# reviewsData = pd.read_csv('restaurant_reviews.csv')
# dataCleaned = reviewsData.dropna()
# dataCleaned = pd.read_csv('analysis.csv')
# # dataCleaned.to_csv('restaurant_reviews.csv', index = False)

# analysisData = generateReviewsAnalysis(dataCleaned, 10)
# analysisData.to_json('review_analysis.json', orient='records', indent=4)
# print('review analysis saved in review_analysis.json')
# df = pd.read_csv('ReviewsScrapped.csv')
# print(df.head())


#main function
if __name__ == "__main__" :
    # url = "https://www.opentable.com/r/toulouse-petit-kitchen-and-lounge-seattle"
    # restaurant_reviews = scrapReviews(url)
    # reviewsData = pd.read_csv('restaurant_reviews.csv')
    # generateReviewsAnalysis(reviewsData, 10)
    convertCSVtoJSON('restaurant_reviews.csv', 'restaurant_reviews.json')



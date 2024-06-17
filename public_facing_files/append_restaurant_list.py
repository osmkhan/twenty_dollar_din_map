import requests
from bs4 import BeautifulSoup
import pandas as pd


def get_soup(url):
    print(f"Fetching content from: {url}")
    response = requests.get(url)
    if response.status_code == 200:
        return BeautifulSoup(response.content, 'html.parser')
    else:
        print(f"Failed to retrieve content from {url}, status code: {response.status_code}")
        return None


def parse_articles(soup):
    articles = []
    for post_card in soup.find_all('div', class_='PostCard_wrapper__uteO3'):
        # Extract article link
        title_link_tag = post_card.find('a', class_='PostCard_titleLink__xUJeU')
        if title_link_tag:
            article_link = f"https://hellgatenyc.com{title_link_tag['href']}"
            # Extract headline
            headline = title_link_tag.find('h3', class_='PostCard_title__d88Gu').get_text().strip()
            # Get article details
            article_page = get_soup(article_link)
            if article_page:
                article_body = extract_article_body(article_page)
                articles.append({
                    'Headline': headline,
                    'Article Link': article_link,
                    'Address': '',
                    'Restaurant Names and Links': '',
                    'Google Maps Address': '',
                    'Restaurant Name': '',
                    'Latitude': '',
                    'Longitude': '',
                    'Link': '',
                    'Unnamed: 10': '',
                    'Unnamed: 11': '',
                    'Unnamed: 12': '',
                    'Article Body': article_body
                })
            else:
                print(f"Failed to fetch article page: {article_link}")
        else:
            print(f"Title link tag not found in post card: {post_card}")
    return articles


def extract_article_body(article_page):
    article_body = article_page.find('div', class_='PostContent_wrapper__oih1Z')
    if article_body:
        return article_body.get_text(separator=' ', strip=True)
    else:
        print("Article body not found")
        return ""


def get_next_page(soup):
    next_button = soup.find('a', class_='Pagination_previousLink__U1GyP')
    if next_button:
        next_page_url = next_button['href']
        return f"https://hellgatenyc.com{next_page_url}"
    else:
        return None


def scrape_articles(start_url):
    all_articles = []
    url = start_url
    while url:
        soup = get_soup(url)
        if soup:
            articles = parse_articles(soup)
            if articles:
                all_articles.extend(articles)
            else:
                print("No articles found on this page.")
            url = get_next_page(soup)
            if not url:
                print("No more pages to scrape.")
        else:
            break
    return all_articles


# looks at all scraped articles, only adds in ones that we don;t have
def new_articles_get_locations(scraped_df, old_list):
    for index, article in scraped_df.iterrows():
        link = article['Article Link']
        print(article)

        if index not in old_list.index.tolist() or link != old_list['Article Link'][index]:
            rest_name = input(f"What's the name of the restaurant contained in the link: {link}?\n")
            raw_address = input(f"Using the format, 456 8th Avenue, Manhattan enter the address for {rest_name}, please:\n")
            socials_website = input(
                f"Optional: Enter the social media or website for {rest_name} (leave blank if none):\n") or ""

            formatted_address = raw_address.replace(' ', '+')
            google_maps_address = formatted_address.replace(',', '%2C')

            article['Restaurant Name'] = rest_name
            article['Google Maps Address'] = google_maps_address
            article['Restaurant Names and Links'] = rest_name + " (" + socials_website + ")"
            #TODO: SWAP OUT THIS MAPS KEY WITH YOUR OWN: EASY TO GET, JUST GOOGLE IT
            geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={google_maps_address}&key=KEY"
            response = requests.get(geocode_url).json()

            if response['status'] == 'OK':
                location = response['results'][0]['geometry']['location']
                lat, lng = location['lat'], location['lng']

                article['Latitude'] = lat
                article['Longitude'] = lng

                # Convert the Series article to a DataFrame and concatenate
                article_df = pd.DataFrame([article])
                old_list = pd.concat([old_list, article_df], ignore_index=True)
            else:
                print(f"Failed to geocode address for restaurant in {link}. Response status: {response['status']}")
    return old_list

start_url = 'https://hellgatenyc.com/author/scott-lynch?after=YXJyYXljb25uZWN0aW9uOjQ5NzI='
articles = scrape_articles(start_url)

if not articles:
    print("No articles found. Please check the URL and the structure of the webpage.")

scraped_articles = pd.DataFrame(articles)
scraped_articles.to_csv('scraped_articles.csv', index=False)
master_list = pd.read_csv("restaurant_list.csv")

if scraped_articles.empty:
    print("The CSV is empty. Please check the scraping logic.")
else:
    new_articles_get_locations(scraped_articles, master_list).to_csv("restaurant_list_for_mapping.csv", index=False)
    print("Scraping complete. Data added")

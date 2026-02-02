import os
import glob
import pandas as pd
from bs4 import BeautifulSoup
import re
import unicodedata
from collections import Counter

def analyze_html(folder_path):
    data = []

    # Grabs every html file in the folder_path
    files = glob.glob(os.path.join(folder_path, "*.html"))

    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            # Reads html
            soup = BeautifulSoup(f.read(), "html.parser")

            # Strips unrelated text not a part of plaintext
            for script_style in soup(["script", "style"]):
                script_style.decompose()
            text = soup.get_text().lower()

            # Uncomment to print the resulting text
            # print(f"Text for {file}: {text}\n")

            # Counts occurrences of keywords and puts them into dictionary
            scores = {
                "Product/Asset": text.count("photo") + text.count("download") + text.count("template"),
                "Legal/Info": text.count("privacy") + text.count("legal") + text.count("terms") + text.count("data"),
            }

            # Finds the category with the bigger amount of keywords
            assigned_category = max(scores, key=scores.get)

            # If there aren't enough of either, file as General
            if scores[assigned_category] < 10:
                assigned_category = "General/Other"

            # Add to a dataframe with these categories
            data.append({
                "Filename": os.path.basename(file),
                "Category": assigned_category,
                "Text_Length": len(text)
            })

    df = pd.DataFrame(data)

    # Save as csv
    df.to_csv("scraping_analysis.csv", index=False)
    return df

def scraping_stats(csv):
    df = pd.read_csv(csv)

    category_counts = df['Category'].value_counts()

    print("--- Text Statistics ---")
    # Average lengths
    avg_text = df.groupby('Category')['Text_Length'].mean().round(2)
    
    # Percentage of each category
    percentages = (df['Category'].value_counts(normalize=True) * 100).round(2)

    # Combine into df
    stats_df = pd.DataFrame({
        'Total Pages': category_counts,
        'Percentage (%)': percentages,
        'Avg Text Length (chars)': avg_text
    })
    
    print(stats_df)

def clean_text(text):
    if not text:
        return ""

    # Normalize Unicode (Fixes "Smart Quotes" and weird characters)
    # NFKC converts characters like ’ or “ into their standard forms
    text = unicodedata.normalize('NFKC', text)

    # Manual Quote Mapping (The missing step)
    # This maps all curly/fancy quotes to their simple ASCII equivalents
    quote_map = {
        '‘': "'", '’': "'", '‚': "'", '‛': "'", # Single quotes/Apostrophes
        '“': '"', '”': '"', '„': '"', '‟': '"', # Double quotes
        '′': "'", '″': '"',                      # Primes (often used as quotes)
    }
    for curly, straight in quote_map.items():
        text = text.replace(curly, straight)

    # Replace all types of whitespace (tabs, newlines, non-breaking spaces) 
    # with a single standard space
    text = re.sub(r'\s+', ' ', text)

    # Strip literal quotes that might wrap the string (like "'Text'")
    text = text.strip().strip("'\"")

    # Remove "Hidden" control characters that sometimes sneak in during scraping
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")

    return text.strip()

def find_categories(data_folder, website):
    categories = set()

    # find homepage filename
    homepage_name = data_folder + "/" + website.replace("https://", "").replace("http://", "").replace("/", "_").rstrip("_") + ".html"

    with open(homepage_name, 'r', encoding='utf-8') as f:
        html = BeautifulSoup(f.read(), 'html.parser')

        # try to find the categories by looking at specific patterns in the homepage
        nav_links = html.find_all('a', href=True)
        for link in nav_links:
            href = link['href']
            # Look for patterns like '/category/' or 'product-category'
            if '/category/' in href or 'product-cat' in href:
                raw_text = link.text.strip()
                category_name = clean_text(raw_text)
                if category_name:
                    categories.add((category_name, href))

    return categories

def extract_links_edd(file_path):
    """
    Extracts the product links from all 'edd_download' cards in a single file.
    """
    product_data = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        
        # Find all the card containers
        cards = soup.find_all('div', class_='edd_download')
        
        for card in cards:
            # Look for the link inside the card
            # Usually, EDD puts the main link in an <a> tag wrapping the title or image
            link_tag = card.find('a', href=True)
            
            if link_tag:
                product_data.append([
                    card.get('id'),      # e.g., 'edd_download_256'
                    link_tag['href']    # e.g., 'https://editablepsd.xyz/product/id-card/'
                ])
                
    return product_data

def find_category_pages(folder, category_url):
    category_url = category_url.replace("https://", "").replace("http://", "").replace("index.html", "").replace("/", "_").rstrip("_")

    matching_files = glob.glob(os.path.join(folder, f"*{category_url}*.html"))

    category_url = category_url.replace("category_", "")
    matching_files.extend(glob.glob(os.path.join(folder, f"*{category_url}*.html")))

    data = []
    for file in matching_files:
        data.extend(extract_links_edd(file))
    
    return data

def find_price(folder, url):
    url = url.replace("../", "").replace("index.html", "")
    url = url.replace("/", "_").rstrip("_")

    matching_files = glob.glob(os.path.join(folder, f"*{url}.html"))
    if (len(matching_files) > 1): 
        print("Warning! more than one matching file")
        for file in matching_files:
            print(file)
    file_path = matching_files[0]

    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        
        # Find all the card containers
        price_container = soup.find_all('span', class_='edd_price')[0]
        price = price_container.text.strip()
    
    return price

def clean_price(price_str):
    if not price_str:
        return 0
    
    # 1. Remove everything except digits and decimal points
    clean_str = re.sub(r'[^\d.]', '', price_str)
    
    try:
        value = float(clean_str)
        
        # 2. Convert to integer if there's no decimal value (e.g., 33.0 -> 33)
        if value.is_integer():
            return int(value)
        
        return value
    except ValueError:
        return 0
    
def get_titles_at_price(category_df, price_type):
    if price_type == "max":
        target = category_df['Price'].max()
    else:
        target = category_df['Price'].min()
    
    # Filter for all items matching that price (handles ties)
    matches = category_df[category_df['Price'] == target]['Title'].tolist()

    return ", ".join(matches)

def get_descriptions(folder, url):
    url = url.replace("index.html", "").replace("../..", "/downloads")
    url = SCRAPING_WEBSITE.rstrip("/") + url
    url = url.replace("https://","").rstrip("/")

    file_name = url.replace("/", "_") + ".html"
    with open(os.path.join(folder, file_name), 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        
        # Find all descriptions
        description_div = soup.find('div', class_='entry-content')

        if description_div:
            # Extract text, using strip=True to clean up whitespace
            # and separator=" " to keep space between paragraphs
            return description_div.get_text(separator=" ", strip=True)
        
    return ""

def analyze_descriptions(text):
    # Standard STOPWORDS logic
    all_text = " ".join(text.astype(str)).lower()
    words = re.findall(r'\b[a-z]{3,}\b', all_text) # Only words 3+ letters
    filtered = [w for w in words if w not in STOPWORDS]
    return ", ".join([f"{w}({c})" for w, c in Counter(filtered).most_common(TOP_N)])



CREATE_CSV = False
SCRAPING_WEBSITE = "https://editablepsd.xyz/"
DATA_FOLDER = "html_files/"
# Basic Stopwords List (Standard English)
STOPWORDS = set([
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "at", "from", "by", 
    "for", "with", "about", "against", "between", "into", "through", "during", "before", 
    "after", "above", "below", "to", "in", "out", "on", "off", "over", "under", "again", 
    "further", "then", "once", "here", "there", "all", "any", "both", "each", "few", "more", 
    "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", 
    "too", "very", "can", "will", "just", "should", "now", "is", "was", "are", "this", "that",
    "it", "you", "your", "our", "their", "we", "be", "has", "have", "been", "do", "does"
])
# Grab the top TOP_N most common words when analyzing descriptions
TOP_N = 5
def main():
    data_folder = "html_files/"
    if CREATE_CSV:
        df = analyze_html(data_folder)
        scraping_stats("scraping_analysis.csv")
    categories = find_categories(data_folder, SCRAPING_WEBSITE + "page/1")
    print("Found the following categories:")
    for cat in categories:
        print(f"{cat}")
    
    prices_and_item = []
    descriptions = []
    for cat in categories:
        links = set()
        data = find_category_pages(DATA_FOLDER, cat[1]);
        for link in data:
            links.add(link[1])

        print(f"Category {cat[0]} has {len(links)} items total.")

        prices = []
        for link in links:
            price = clean_price(find_price(DATA_FOLDER, link))
            desc = get_descriptions(data_folder, link)

            clean_link = link.replace("index.html", "").replace("../", "").replace("/downloads/", "").rstrip("/")

            prices_and_item.append({
                "Category" : cat[0],
                "Title"    : clean_link,
                "Price"    : price}
            )
            prices.append(price)

            descriptions.append({
                "Category": cat[0],
                "Title": clean_link,
                "Description": desc
            })

    # Process price information and get statistics
    df_price = pd.DataFrame(prices_and_item)
    summary_price = df_price.groupby('Category')['Price'].agg(['mean', 'max', 'min']).reset_index()

    summary_price = summary_price.round(2)
    print(summary_price.to_string(index=False))

    summary_price['Max_Items'] = summary_price['Category'].apply(
    lambda x: get_titles_at_price(df_price[df_price['Category'] == x], 'max'))
    summary_price['Min_Items'] = summary_price['Category'].apply(
    lambda x: get_titles_at_price(df_price[df_price['Category'] == x], 'min'))

    summary_price.to_csv('category_price.csv', index=False)

    # Process descriptions and get stats
    df_desc = pd.DataFrame(descriptions)

    keyword_summary = df_desc.groupby('Category')['Description'].apply(analyze_descriptions).reset_index()
    keyword_summary.columns = ['Category', 'Top_Keywords']

    keyword_summary.to_csv('category_descriptions.csv', index=False)

if __name__ == "__main__":
    main()

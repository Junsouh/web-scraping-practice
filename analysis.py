import os
import glob
import pandas as pd
from bs4 import BeautifulSoup
import re
import unicodedata

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
        




        
         

CREATE_CSV = False
SCRAPING_WEBSITE = "https://editablepsd.xyz/"
DATA_FOLDER = "html_files/"
def main():
    data_folder = "html_files/"
    if CREATE_CSV:
        df = analyze_html(data_folder)
        scraping_stats("scraping_analysis.csv")
    categories = find_categories(data_folder, SCRAPING_WEBSITE + "page/1")
    print("Found the following categories:")
    for cat in categories:
        print(f"{cat}")
    
    for cat in categories:
        links = set()
        data = find_category_pages(DATA_FOLDER, cat[1]);
        for link in data:
            links.add(link[1])

        print(f"Category {cat[0]} had {len(links)} items total.\n")

    



    


if __name__ == "__main__":
    main()

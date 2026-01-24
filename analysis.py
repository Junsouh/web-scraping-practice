import os
import glob
import pandas as pd
from bs4 import BeautifulSoup

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

def main():
    data_folder = "html_files/"
    df = analyze_html(data_folder)
    scraping_stats("scraping_analysis.csv")

if __name__ == "__main__":
    main()

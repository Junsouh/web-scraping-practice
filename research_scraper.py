import nodriver as uc
import asyncio
import os
from collections import deque
import shutil

SCRAPING_WEBSITE = "https://editablepsd.xyz/"

async def save_page(page, url, folder):
    try:
        # Grab HTML
        content = await page.get_content()

        # Make sure url works as a filename
        filename = url.replace("https://", "").replace("http://", "").replace("/", "_").rstrip("_") + ".html"

        path = os.path.join(folder, filename)

        # Write to file
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Successfully saved {url}")

    except Exception as e:
        # If saving fails for any reason, print error
        print(f"Failed to save {url}: {e}")

async def main():
    # Start the browser
    browser = await uc.start(headless=True)
    
    # Delete old folder for data
    data_folder = "html_files/"
    if os.path.exists(data_folder):
        print(f"Cleaning old data from data folder\n")
        shutil.rmtree(data_folder)

    # Create new folder for data
    os.makedirs(data_folder)

    # Create queue and set for BFS
    links_queue = deque([SCRAPING_WEBSITE])
    links_found = {SCRAPING_WEBSITE}
    SEARCH_DEPTH = 10

    # Begin BFS
    current_depth = 0
    links_count = 0
    while (len(links_queue) > 0 and current_depth < SEARCH_DEPTH):
        links_count = len(links_found)
        print(f"\n--- Scraping Depth {current_depth} ---")
        
        # Count current amount of links to proceed layer by layer
        link_count = len(links_queue)

        for _ in range(link_count):
            # Pop one url
            current_url = links_queue.popleft()

            print(f"Visiting: {current_url}")
            page = await browser.get(current_url)

            if (current_url != SCRAPING_WEBSITE):
                # Save the page while we have it
                await page.sleep(10)
                await save_page(page, current_url, data_folder)

            # Find all tags with href under an anchor tag
            all_tags = await page.select_all('a[href]')
            for tag in all_tags:
                # Find the href in the tag
                href = tag['href']

                # If there is none, continue
                if not href: 
                    continue

                full_link = ""

                # If a relative link, add the website url to it - 
                # otherwise, use it as it is
                if href.startswith('/'):
                    full_link = SCRAPING_WEBSITE.rstrip('/') + href
                elif SCRAPING_WEBSITE in href:
                    full_link = href
                
                # If the link has not been found yet, add it to the queue and set
                if full_link and (full_link not in links_found):
                    links_found.add(full_link)
                    links_queue.append(full_link)


        current_depth += 1

    print(f"\n Done, found and saved {links_count} pages")
    print(f"{len(links_found) - links_count} left to scrape")

if __name__ == '__main__':
    # This is how you run an 'async' function in nodriver
    uc.loop().run_until_complete(main())
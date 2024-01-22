import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from concurrent.futures import ThreadPoolExecutor
import logging
import argparse
from colorama import init, Fore, Style

init(autoreset=True)  # Initialize colorama

def fetch_js_urls(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tags = soup.find_all('script')
            base_url = response.url
            js_urls = [urljoin(base_url, tag.get('src')) for tag in script_tags if tag.get('src')]
            return base_url, js_urls
        else:
            logging.error(f"Error: Unable to fetch the URL {url} (Status Code: {response.status_code})")
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")

def download_js_file(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)

        # Raise an HTTPError for bad responses (4xx and 5xx status codes)
        response.raise_for_status()

        return response.text
    except requests.exceptions.HTTPError as errh:
        # Omit the logging message for HTTP errors
        return None
    except Exception as e:
        # Omit the logging message for general errors
        return None

def extract_paths_from_js(js_content):
    paths = re.findall(r'["\']\s*\/([a-zA-Z0-9_/?=&.-]+)\s*["\']', js_content)
    filtered_paths = [path.strip('"\'') for path in paths if not path.startswith('//') and path != '/']
    return filtered_paths

def process_js_url(base_url, js_url, output_file, processed_urls):
    if js_url not in processed_urls:
        processed_urls.add(js_url)
        js_content = download_js_file(js_url)
        if js_content:
            paths = extract_paths_from_js(js_content)
            if paths:
                with open(output_file, 'a') as f:
                    for path in paths:
                        full_url = urljoin(base_url, path)
                        f.write(full_url + '\n')
                        print(Fore.GREEN + full_url)  # Green color for URLs
            else:
                # Omit the logging message for "No relevant paths found"
                pass
        else:
            # Omit the logging message for "Failed to download the JavaScript file"
            pass

def process_url_list(file_path, output_file):
    processed_urls = set()

    with open(file_path, 'r') as file:
        urls = file.read().splitlines()

    if urls:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for url in urls:
                base_url, js_urls = fetch_js_urls(url)
                if js_urls:
                    for js_url in js_urls:
                        futures.append(executor.submit(process_js_url, base_url, js_url, output_file, processed_urls))
            for future in futures:
                future.result()
    else:
        logging.info("No URLs found in the list.")

def main():
    print(Fore.CYAN + Style.BRIGHT + "Active Fuzzer is running\nThis tool is developed by Mr-k0anti")

    parser = argparse.ArgumentParser(description="Fetch and analyze JavaScript files from a URL or a list of URLs.")
    parser.add_argument("-u", "--url", help="URL to analyze")
    parser.add_argument("-l", "--list", help="File containing a list of URLs to analyze")
    parser.add_argument("-o", "--output", help="Output file to save the URLs", default="output.txt")
    args = parser.parse_args()

    if args.url:
        base_url, js_urls = fetch_js_urls(args.url)
        if js_urls:
            with ThreadPoolExecutor(max_workers=5) as executor:
                for js_url in js_urls:
                    executor.submit(process_js_url, base_url, js_url, args.output, set())
        else:
            logging.info("No JavaScript source URLs found.")

    elif args.list:
        process_url_list(args.list, args.output)

if __name__ == "__main__":
    logging.basicConfig(format='%(message)s', level=logging.INFO)  # Set the desired log level and remove INFO:root:
    main()

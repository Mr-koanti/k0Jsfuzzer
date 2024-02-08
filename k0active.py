import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from concurrent.futures import ThreadPoolExecutor
import logging
import argparse
from colorama import init, Fore, Style
import urllib3

init(autoreset=True)  # Initialize colorama
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # Disable SSL warnings

def fetch_js_urls(url):
    try:
        # Specify a custom user agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Disable SSL verification and suppress warnings (not recommended for production)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(url, headers=headers, timeout=10, verify=False)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tags = soup.find_all('script')
            base_url = response.url
            js_urls = [urljoin(base_url, tag.get('src')) for tag in script_tags if tag.get('src')]
            return base_url, js_urls
        else:
            logging.error(f"Error: Unable to fetch the URL {url} (Status Code: {response.status_code})")
            return None
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
        return None

def download_js_file(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Disable SSL verification and suppress warnings (not recommended for production)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(url, headers=headers, timeout=10, verify=False)

        # Raise an HTTPError for bad responses (4xx and 5xx status codes)
        response.raise_for_status()

        return response.text
    except requests.exceptions.HTTPError as errh:
        # Omit the logging message for HTTP errors
        return None
    except Exception as e:
        # Omit the logging message for general errors
        return None

def is_valid_url(url, excluded_extensions):
    parsed_url = urlparse(url)
    path = parsed_url.path
    extension = path.split('.')[-1].lower()

    return extension not in excluded_extensions

def extract_paths_from_js(js_content):
    paths = re.findall(r'["\']\s*\/([a-zA-Z0-9_/?=&.-]+)\s*["\']', js_content)
    filtered_paths = [path.strip('"\'') for path in paths if not path.startswith('//') and path != '/']
    return filtered_paths

def process_js_url(base_url, js_url, output_file, processed_urls, excluded_extensions, just_paths):
    if js_url not in processed_urls:
        processed_urls.add(js_url)
        js_content = download_js_file(js_url)
        if js_content:
            paths = extract_paths_from_js(js_content)
            if paths:
                with open(output_file, 'a') as f:
                    for path in paths:
                        result = path if just_paths else urljoin(base_url, path)
                        if is_valid_url(result, excluded_extensions):
                            f.write(result + '\n')
                            print(Fore.GREEN + result)  # Green color for valid paths/URLs
            else:
                # Omit the logging message for "No relevant paths found"
                pass
        else:
            # Omit the logging message for "Failed to download the JavaScript file"
            pass

def process_url_list(file_path, output_file, excluded_extensions, just_paths):
    processed_urls = set()

    with open(file_path, 'r') as file:
        urls = file.read().splitlines()

    if urls:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for url in urls:
                result = fetch_js_urls(url)
                if result:
                    base_url, js_urls = result
                    for js_url in js_urls:
                        futures.append(executor.submit(process_js_url, base_url, js_url, output_file, processed_urls, excluded_extensions, just_paths))
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
    parser.add_argument("-jp", "--just-paths", action="store_true", help="Extract just paths instead of full URLs")
    args = parser.parse_args()

    excluded_extensions = ['js', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'svg']

    if args.url:
        result = fetch_js_urls(args.url)
        if result:
            base_url, js_urls = result
            with ThreadPoolExecutor(max_workers=5) as executor:
                for js_url in js_urls:
                    executor.submit(process_js_url, base_url, js_url, args.output, set(), excluded_extensions, args.just_paths)
        else:
            logging.info("No JavaScript source URLs found.")

    elif args.list:
        process_url_list(args.list, args.output, excluded_extensions, args.just_paths)

if __name__ == "__main__":
    logging.basicConfig(format='%(message)s', level=logging.INFO)  # Set the desired log level and remove INFO:root:
    main()

from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
import requests
import uuid
from urllib.parse import urljoin, urlparse
from flyflowclient import Flyflow
import concurrent.futures

app = Flask(__name__)
CORS(app)

# Helper function to ensure URLs have https schema
def ensure_https(url):
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        return f"https://{url}"
    return url

# Function to recursively scrape text from a URL
def scrape_text(url, base_url, visited=None):
    if visited is None:
        visited = set()

    if url in visited:
        return ""

    visited.add(url)
    texts = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Sec-Ch-Ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"macOS"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-site',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        texts.append('\n'.join(soup.stripped_strings))

        # Adjust link processing to handle relative paths correctly
        links = [
            ensure_https(urljoin(base_url, link['href']))
            for link in soup.find_all('a', href=True)
            if urlparse(urljoin(base_url, link['href'])).netloc == urlparse(base_url).netloc
        ]

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(scrape_text, link, base_url, visited) for link in links]
            for future in concurrent.futures.as_completed(futures):
                texts.append(future.result())

    except requests.exceptions.RequestException as e:
        # Log the error and skip adding it to the texts
        print(f"Error scraping {url}: {str(e)}")

    return '\n'.join(texts)

# Function to remove duplicate paragraphs and truncate to 1,000,000 characters
def process_text(text):
    paragraphs = text.split('\n')
    unique_paragraphs = list(dict.fromkeys(paragraphs))  # Remove duplicates while preserving order
    unique_text = ' '.join(unique_paragraphs).replace('\n', ' ')
    return unique_text[:1000000]  # Truncate to 1,000,000 characters

# Endpoint to create a new Flyflow agent
@app.route('/create_agent', methods=['POST'])
def create_agent():
    data = request.json
    if 'urls' not in data:
        return jsonify({'error': 'Missing urls parameter'}), 400

    urls = [ensure_https(url) for url in data['urls']]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(scrape_text, url, url) for url in urls]
        customer_docs = "\n".join(future.result() for future in concurrent.futures.as_completed(futures))

    processed_docs = process_text(customer_docs)

    # Flyflow client initialization
    client = Flyflow(api_key='demo')

    # Create a new agent with unique name
    agent_name = f"Alice_Docs_Agent_{uuid.uuid4()}"

    agent = client.upsert_agent(
        name=agent_name,
        system_prompt=f"""
        You are an expert customer support agent
        
        Customer docs: {processed_docs}
        
        Style Guide 
        - Respond to the user's answer to the previous questions with a full sentence responding to their answer before asking the next question
        - Only include one idea at a time in your response  
        - *Do not include* lists of numbers or asterisks in your response*
        
        Actions you can take:
        - hangup - only do this once both the user and the assistant have said goodbye and the conversation has reached a logical ending point. Never say "hangup" or announce that you're hanging up
        """,
        initial_message="Hi, this is Alice. How can I help?",
        llm_model="gpt-4o",
        voice_id="female-young-american-strong",
        filler_words=True,
        actions=[
            {
                "name": "hangup",
                "instructions": "End the call after the user and assistant have said goodbye. Make sure to only call the hangup function once the assistant has responded!"
            }
        ],
        filler_words_whitelist=["Yeah.", "Hmm.", "Sure.", "Let me see.", "Alright.", "Well.", ""],
    )

    # Return the phone number as JSON
    return jsonify({"phone_number": agent['phone_number']})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

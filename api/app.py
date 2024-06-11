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

    try:
        response = requests.get(url)
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

    except Exception as e:
        texts.append(f"Error scraping {url}: {str(e)}")

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

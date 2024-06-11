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
        texts.append(' '.join(soup.stripped_strings).replace('\n', ' '))

        links = [urljoin(url, link['href']) for link in soup.find_all('a', href=True) if urlparse(urljoin(url, link['href'])).netloc == urlparse(base_url).netloc]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(scrape_text, link, base_url, visited) for link in links]
            for future in concurrent.futures.as_completed(futures):
                texts.append(future.result())

    except Exception as e:
        texts.append(f"Error scraping {url}: {str(e)}")

    return ' '.join(texts)

# Endpoint to create a new Flyflow agent
@app.route('/create_agent', methods=['POST'])
def create_agent():
    data = request.json
    if 'urls' not in data:
        return jsonify({'error': 'Missing urls parameter'}), 400

    urls = data['urls']

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(scrape_text, url, url) for url in urls]
        customer_docs = " ".join(future.result() for future in concurrent.futures.as_completed(futures))

    # Flyflow client initialization
    client = Flyflow(api_key='demo')

    # Create a new agent with unique name
    agent_name = f"Alice_Docs_Agent_{uuid.uuid4()}"

    agent = client.upsert_agent(
        name=agent_name,
        system_prompt=f"""
        You are an expert customer support agent
        
        Customer docs: {customer_docs}
        
        Style Guide 
        - Respond to the user's answer to the previous questions with a full sentence responding to their answer before asking the next question
        - Only include one idea at a time in your response  
        - *Do not include* lists of numbers or asterisks in your response *
        """,
        initial_message="Hi, this is Alice. How can I help?",
        llm_model="gpt-4o",
        voice_id="female-young-american-strong",
    )

    # Return the phone number as JSON
    return jsonify({"phone_number": agent['phone_number']})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

#!/usr/bin/env python3
"""Azure AI Search diagnostic script"""

import requests
import os
import json
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_diagnostics():
    print('HAVAS Chatbot - Azure AI Search Diagnostics')
    print('=' * 60)
    
    # Check environment variables
    print('\n1. Checking environment variables...')
    required_vars = [
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_KEY', 
        'AZURE_OPENAI_DEPLOYMENT',
        'AZURE_OPENAI_TRANSLATION_DEPLOYMENT',
        'AZURE_SEARCH_ENDPOINT',
        'AZURE_SEARCH_KEY',
        'AZURE_SEARCH_INDEX'
    ]
    
    missing_vars = []
    for var_name in required_vars:
        value = os.getenv(var_name)
        if value:
            print(f'   {var_name}: {value[:20]}...')
        else:
            print(f'   {var_name}: NOT CONFIGURED')
            missing_vars.append(var_name)
    
    if missing_vars:
        print(f'\n{len(missing_vars)} required environment variables are missing.')
        sys.exit(1)
    
    # Test Azure Search Index
    print('\n2. Checking Azure AI Search index...')
    try:
        index_url = f"{os.getenv('AZURE_SEARCH_ENDPOINT')}/indexes/{os.getenv('AZURE_SEARCH_INDEX')}?api-version=2023-11-01"
        headers = {
            'api-key': os.getenv('AZURE_SEARCH_KEY')
        }
        
        response = requests.get(index_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f'   Index found: {data["name"]}')
            print(f'   Total fields: {len(data["fields"])}')
            
            # Show important fields
            print('\n   Index fields:')
            for field in data['fields']:
                searchable = 'searchable' if field.get('searchable', False) else 'not searchable'
                key = 'key' if field.get('key', False) else 'not key'
                print(f'   {key}, {searchable}: {field["name"]} ({field["type"]})')
        else:
            print(f'   Error accessing index:')
            print(f'      Status: {response.status_code}')
            print(f'      Message: {response.text}')
            return
        
    except Exception as error:
        print('   Error accessing index:')
        print(f'      Message: {str(error)}')
        return
    
    # Test simple search
    print('\n3. Testing simple search...')
    try:
        search_url = f"{os.getenv('AZURE_SEARCH_ENDPOINT')}/indexes/{os.getenv('AZURE_SEARCH_INDEX')}/docs/search?api-version=2023-11-01"
        
        payload = {
            "search": "*",
            "top": 3,
            "select": "*"
        }
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': os.getenv('AZURE_SEARCH_KEY')
        }
        
        search_response = requests.post(search_url, json=payload, headers=headers)
        
        if search_response.status_code == 200:
            results = search_response.json().get('value', [])
            print(f'   Search successful: {len(results)} documents found')
            
            if results:
                print('\n   Sample of the first document:')
                doc = results[0]
                for i, (key, value) in enumerate(doc.items()):
                    if i >= 5:  # Only show the first 5 fields
                        break
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + '...'
                    print(f'      {key}: {value}')
            else:
                print('   No documents found in the index')
        else:
            print('   Error in search:')
            print(f'      Status: {search_response.status_code}')
            print(f'      Message: {search_response.text}')
        
    except Exception as error:
        print('   Error in search:')
        print(f'      Message: {str(error)}')
    
    # Test search with specific query
    print('\n4. Testing specific search...')
    try:
        test_queries = ['HAVAS', 'information', 'company', 'service']
        
        for query in test_queries:
            search_url = f"{os.getenv('AZURE_SEARCH_ENDPOINT')}/indexes/{os.getenv('AZURE_SEARCH_INDEX')}/docs/search?api-version=2023-11-01"
            
            payload = {
                "search": query,
                "top": 2,
                "select": "*"
            }
            
            headers = {
                'Content-Type': 'application/json',
                'api-key': os.getenv('AZURE_SEARCH_KEY')
            }
            
            search_response = requests.post(search_url, json=payload, headers=headers)
            
            if search_response.status_code == 200:
                results = search_response.json().get('value', [])
                print(f'   Query "{query}": {len(results)} results')
            else:
                print(f'   Error in query "{query}": {search_response.text}')
        
    except Exception as error:
        print(f'   Error in specific search: {str(error)}')
    
    # Test Azure OpenAI
    print('\n5. Checking Azure OpenAI...')
    try:
        deployment_url = f"{os.getenv('AZURE_OPENAI_ENDPOINT')}/openai/deployments?api-version=2023-05-15"
        headers = {
            'api-key': os.getenv('AZURE_OPENAI_KEY')
        }
        
        openai_response = requests.get(deployment_url, headers=headers)
        
        if openai_response.status_code == 200:
            print('   OpenAI connection successful')
            
            deployments = openai_response.json().get('data', [])
            target_deployment = next((d for d in deployments if d.get('id') == os.getenv('AZURE_OPENAI_DEPLOYMENT')), None)
            
            if target_deployment:
                print(f'   Deployment found: {target_deployment["id"]}')
                print(f'   Model: {target_deployment.get("model", "N/A")}')
            else:
                print(f'   Deployment "{os.getenv("AZURE_OPENAI_DEPLOYMENT")}" not found')
                print('   Available deployments:')
                for d in deployments:
                    print(f'      - {d.get("id", "N/A")} ({d.get("model", "N/A")})')
        else:
            print('   Error connecting to OpenAI:')
            print(f'      Status: {openai_response.status_code}')
            print(f'      Message: {openai_response.text}')
        
    except Exception as error:
        print('   Error connecting to OpenAI:')
        print(f'      Message: {str(error)}')
    
    # Test complete integration
    print('\n6. Testing complete integration...')
    try:
        # Simulate a real query
        test_message = 'Hello, what services does HAVAS offer?'
        print(f'   Test query: "{test_message}"')
        
        # Search
        search_url = f"{os.getenv('AZURE_SEARCH_ENDPOINT')}/indexes/{os.getenv('AZURE_SEARCH_INDEX')}/docs/search?api-version=2023-11-01"
        
        payload = {
            "search": test_message,
            "top": 2,
            "select": "*"
        }
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': os.getenv('AZURE_SEARCH_KEY')
        }
        
        search_response = requests.post(search_url, json=payload, headers=headers)
        
        if search_response.status_code == 200:
            search_results = search_response.json().get('value', [])
            print(f'   Documents found: {len(search_results)}')
            
            # Generate context
            context = ''
            if search_results:
                context_parts = []
                for doc in search_results:
                    fields = list(doc.keys())
                    text_field = next((f for f in fields if f.lower() in ['content', 'text', 'description', 'body']), fields[0])
                    
                    doc_content = doc.get(text_field, json.dumps(doc)[:200])
                    context_parts.append(str(doc_content))
                
                context = '\n\n'.join(context_parts)
            
            # Test OpenAI with context
            if context:
                api_url = f"{os.getenv('AZURE_OPENAI_ENDPOINT')}/openai/deployments/{os.getenv('AZURE_OPENAI_DEPLOYMENT')}/chat/completions?api-version=2024-12-01-preview"
                
                openai_payload = {
                    "messages": [
                        { 
                            "role": "system", 
                            "content": f"You are an assistant of HAVAS. Context: {context[:500]}" 
                        },
                        { "role": "user", "content": test_message }
                    ],
                    "max_completion_tokens": 150,
                    "temperature": 0.7
                }
                
                openai_headers = {
                    'Content-Type': 'application/json',
                    'api-key': os.getenv('AZURE_OPENAI_KEY')
                }
                
                openai_response = requests.post(api_url, json=openai_payload, headers=openai_headers)
                
                if openai_response.status_code == 200:
                    ai_response = openai_response.json()['choices'][0]['message']['content']
                    print('   AI response generated successfully')
                    print(f'   Preview: "{ai_response[:100]}..."')
                    print('\n   Complete integration is working correctly!')
                else:
                    print(f'   Error in OpenAI: {openai_response.text}')
            else:
                print('   No context available, but OpenAI is working')
        else:
            print(f'   Error in integration search: {search_response.text}')
        
    except Exception as error:
        print(f'   Error in integration test: {str(error)}')
    
    print('\n' + '=' * 60)
    print('Diagnostics completed')
    print('\nSuggestions:')
    print('   - If there are no documents, check the indexing process')
    print('   - Ensure that search fields are marked as "searchable"')  
    print('   - Consider using semantic search for better results')
    print('   - Check server logs for more details during queries')

if __name__ == '__main__':
    # Run diagnostics
    try:
        run_diagnostics()
    except Exception as error:
        print(f'Error during diagnostics: {str(error)}')
        sys.exit(1)

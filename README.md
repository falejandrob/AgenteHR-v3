# HAVAS TV Report Assistant

AI-powered conversational assistant specialized in television reporting and media content, built with Flask and Azure OpenAI.

## Overview

This application is a modern web-based chatbot designed specifically for HAVAS television reporting teams. It leverages Azure AI Search for intelligent document retrieval and Azure OpenAI for natural language processing, enabling users to query television reports, media content, and related documentation through an intuitive conversational interface.

### Key Features

- **Conversational AI**: Powered by Azure OpenAI (GPT-4.1-mini) for intelligent responses
- **Document Search**: Integrated Azure AI Search with vector-based document retrieval
- **Multi-language Support**: Responds in the same language as the query (Spanish, French, English, etc.)
- **Session Management**: Maintains conversation context across sessions
- **Rate Limiting**: Built-in protection with configurable request limits
- **Modern UI**: Clean, responsive web interface with real-time chat
- **Health Monitoring**: System health checks and diagnostics

## Architecture

### Core Components

1. **Flask Web Server** (`app.py`): Main application server handling HTTP requests and API endpoints
2. **TV Agent** (`agents/tv_agent.py`): Core AI agent responsible for processing messages and generating responses
3. **Azure Search Client** (`tools/azure_search.py`): Document retrieval system using Azure AI Search
4. **Memory Manager** (`memory/simple_memory.py`): Session and conversation memory management
5. **LangChain Configuration** (`config/langchain_config.py`): Azure OpenAI integration and model configuration

### Technology Stack

- **Backend**: Flask 3.0, Python 3.10+
- **AI/ML**: LangChain, Azure OpenAI API
- **Search**: Azure AI Search with vector embeddings
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Security**: Flask-Limiter for rate limiting, CORS support

## Installation

### Prerequisites

- Python 3.10 or higher
- Azure OpenAI Service subscription
- Azure AI Search service
- Valid Azure API keys

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AgenteHR-v3
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment configuration**
   
   Copy `.env.example` to `.env` and configure your Azure credentials:
   ```env
   # Azure OpenAI Configuration
   AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
   AZURE_OPENAI_KEY=your-openai-api-key
   AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
   AZURE_OPENAI_API_VERSION=2025-01-01-preview
   AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
   AZURE_OPENAI_MAX_COMPLETION_TOKENS=6000

   # Azure AI Search Configuration
   AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
   AZURE_SEARCH_KEY=your-search-api-key
   AZURE_SEARCH_INDEX=your-index-name
   AZURE_SEARCH_VECTOR=true
   AZURE_SEARCH_ONLY=true
   AZURE_SEARCH_VECTOR_FIELD=content_embedding
   AZURE_SEARCH_VECTOR_K=25

   # Application Configuration
   PORT=3000
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

   The application will be available at `http://localhost:3000`

## API Reference

### Endpoints

#### `GET /`
Serves the main chat interface.

#### `POST /api/chat`
Main chat endpoint for processing user messages.

**Request Body:**
```json
{
  "message": "What reports are available about sports coverage?",
  "sessionId": "user-session-123"
}
```

**Response:**
```json
{
  "response": "Based on the available reports...",
  "documentsFound": 5,
  "hasContext": true,
  "session_info": {
    "session_id": "user-session-123",
    "message_count": 3,
    "last_activity": "2025-08-28T14:30:00",
    "created": "2025-08-28T14:25:00"
  },
  "processing_time": 1.23,
  "timestamp": "2025-08-28T14:30:00"
}
```

**Rate Limit:** 30 requests per minute per IP

#### `POST /api/new-conversation`
Starts a new conversation session.

**Request Body:**
```json
{
  "sessionId": "user-session-123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "New conversation started",
  "sessionId": "user-session-123",
  "timestamp": "2025-08-28T14:30:00"
}
```

**Rate Limit:** 10 requests per minute per IP

#### `GET /api/health`
System health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-28T14:30:00",
  "version": "2.0"
}
```

#### `GET /api/debug/sessions`
Debug endpoint for viewing active sessions (development only).

**Response:**
```json
{
  "active_sessions": {
    "default": {
      "session_id": "default",
      "message_count": 5,
      "last_activity": "2025-08-28T14:30:00",
      "created": "2025-08-28T14:25:00"
    }
  },
  "timestamp": "2025-08-28T14:30:00"
}
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI service endpoint | Yes | - |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key | Yes | - |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name | Yes | gpt-4o-mini |
| `AZURE_OPENAI_API_VERSION` | API version | No | 2025-01-01-preview |
| `AZURE_OPENAI_MAX_COMPLETION_TOKENS` | Maximum tokens per response | No | 6000 |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint | Yes | - |
| `AZURE_SEARCH_KEY` | Azure AI Search API key | Yes | - |
| `AZURE_SEARCH_INDEX` | Search index name | Yes | - |
| `AZURE_SEARCH_VECTOR` | Enable vector search | No | true |
| `AZURE_SEARCH_ONLY` | Use only Azure Search (no fallback) | No | true |
| `AZURE_SEARCH_VECTOR_FIELD` | Vector field name | No | content_embedding |
| `AZURE_SEARCH_VECTOR_K` | Number of search results | No | 25 |
| `PORT` | Server port | No | 3000 |
| `FLASK_DEBUG` | Debug mode | No | false |

### Model Support

The application is optimized for Azure OpenAI's reasoning models, particularly:
- **GPT-4.1-mini**: Primary model for TV reporting queries
- **GPT-4o-mini**: Alternative model option
- **o3-mini**: Experimental reasoning model support

Special handling is implemented for reasoning models that don't support standard parameters like temperature or top_p.

## Usage Examples

### Basic Query
```javascript
fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: "What are the latest sports reports?",
    sessionId: "user-123"
  })
})
```

### Starting New Conversation
```javascript
fetch('/api/new-conversation', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    sessionId: "user-123"
  })
})
```

## Development

### Project Structure

```
AgenteHR-v3/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── .env.example             # Environment configuration template
├── agents/
│   └── tv_agent.py          # Main AI agent
├── config/
│   └── langchain_config.py  # Azure OpenAI configuration
├── memory/
│   └── simple_memory.py     # Session memory management
├── tools/
│   └── azure_search.py      # Document search integration
├── public/                  # Frontend assets
│   ├── index.html          # Main chat interface
│   ├── css/styles.css      # Styling
│   └── js/chat.js          # Frontend JavaScript
└── tests/
    └── diagnostic.py       # System diagnostics
```

### Running in Development Mode

```bash
export FLASK_DEBUG=true
python app.py
```

### Testing

Run the diagnostic script to verify system configuration:

```bash
python tests/diagnostic.py
```

## Troubleshooting

### Common Issues

1. **Module Import Errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Verify Python version compatibility (3.10+)

2. **Azure API Connection Issues**
   - Verify API keys and endpoints in `.env` file
   - Check Azure service quotas and availability
   - Run diagnostic script: `python tests/diagnostic.py`

3. **Search Results Issues**
   - Ensure Azure AI Search index is properly configured
   - Verify vector embeddings are available if using vector search
   - Check index permissions and API keys

4. **Performance Issues**
   - Adjust `AZURE_OPENAI_MAX_COMPLETION_TOKENS` if responses are slow
   - Consider reducing `AZURE_SEARCH_VECTOR_K` for faster searches
   - Monitor rate limits and adjust client request patterns

### Logging

The application uses Python's built-in logging with INFO level by default. Key log categories:

- **Application**: General server operations
- **Agent**: Message processing and AI interactions
- **Search**: Document retrieval operations
- **Memory**: Session management
- **Config**: Configuration and initialization

## Security Considerations

- API keys stored in environment variables only
- Rate limiting implemented on all endpoints
- CORS configured for frontend integration
- Input validation on all user inputs
- Session isolation for multi-user support

## License

Internal HAVAS project. All rights reserved.

## Support

For technical support or configuration issues:
1. Run the diagnostic script: `python tests/diagnostic.py`
2. Check application logs for error details
3. Verify Azure service status and quotas
4. Review environment configuration against `.env.example`
# Realtime AI Backend

A Python-based backend for building real-time AI applications with OpenAI's APIs. This project provides a simple yet powerful interface for creating interactive AI agents with voice and text capabilities.

## Project Structure

```
Realtime_AI_Backend/
├── app2.py           # Main application entry point
├── test.py           # Test and example usage
└── requirements.txt  # Project dependencies
```

## Quick Start

### Prerequisites

- Python 3.9 or higher
- OpenAI API key
- pip or uv package manager

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Kashika221/Realtime_AI_Backend.git
   cd Realtime_AI_Backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your OpenAI API key as an environment variable:
   ```bash
   export OPENAI_API_KEY='your_api_key_here'
   ```

### Running the Application

```bash
python app2.py
```

### Testing

Run the test file to see example usage:

```bash
python test.py
```

## How It Works

The project demonstrates real-time AI interactions using OpenAI's Realtime API. The main application (`app2.py`) handles:

- Establishing WebSocket connections with OpenAI's Realtime API
- Managing conversational state and context
- Processing both text and audio inputs
- Handling real-time streaming responses
- Managing session configuration

## Use Cases

- Interactive voice assistants
- Real-time conversational AI chatbots
- Audio-based AI applications
- Low-latency AI interactions
- Voice-to-voice conversations

## Key Features

- Low-latency real-time communication
- WebSocket-based streaming
- Support for multiple input modalities
- Async/await architecture for efficient I/O
- Easy integration with OpenAI's latest AI models

## Dependencies

Check `requirements.txt` for all required packages. Core dependencies include:

- `openai` - OpenAI Python SDK
- `websockets` - WebSocket protocol support
- `aiohttp` - Async HTTP client
- `asyncio` - Python's async I/O library

## Development

To modify or extend the project:

1. Edit `app2.py` to customize the main application logic
2. Update `test.py` to add new test cases or examples
3. Modify `requirements.txt` if adding new dependencies

## Troubleshooting

**API Key Not Found**: Ensure your OpenAI API key is set in environment variables:
```bash
echo $OPENAI_API_KEY  # Verify it's set
```

**Connection Errors**: Check your internet connection and ensure the OpenAI API is accessible.

**Import Errors**: Verify all dependencies are installed:
```bash
pip install -r requirements.txt
```

## Documentation

For more information about OpenAI's Realtime API, refer to the official documentation:
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime-api)
- [OpenAI Python SDK](https://github.com/openai/openai-python)

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Feel free to:
- Fork the repository
- Create a feature branch
- Make your changes
- Submit a pull request

## Support

For issues or questions:
- Check the test.py file for usage examples
- Review OpenAI's API documentation
- Open an issue on GitHub

---

**Built for real-time AI interactions with OpenAI's Realtime API**

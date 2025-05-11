# Tetra: AI-Powered Shopping and Assistant

Tetra is an AI-powered desktop application that combines e-commerce automation with conversational AI capabilities. Built with Python and utilizing Google's Gemini API, Tetra can help users search for products, analyze images, check weather information, and engage in natural conversations.

## 🌟 Features

- **E-commerce Integration**: Automates product search and shopping on HepsiBurada, with smart product selection and comparison
- **Image Analysis**: Uploads and analyzes images with detailed descriptions
- **Weather Information**: Retrieves current weather data for specified locations
- **Multilingual Support**: Supports English, Turkish, Spanish, German, French, and Russian
- **Voice Output**: Text-to-speech functionality for an interactive experience
- **Intuitive GUI**: User-friendly interface with customizable settings

## 🔧 Technologies

- **Python**: Core programming language
- **PyQt5**: GUI framework
- **Selenium**: Web automation for e-commerce functionality
- **Google Gemini API**: Provides AI capabilities for natural language processing and image analysis
- **WeatherAPI**: Retrieves current weather information
- **pygame**: Handles audio playback for text-to-speech
- **gTTS (Google Text-to-Speech)**: Converts text to speech in multiple languages

## 📋 Requirements

 ```
 pip3 install -r requirements.txt
 ```

## 🔑 API Keys Setup

Create a `.env` file in the project root with the following format:
```
Gemini_Api_Key=your_gemini_api_key_here
Weather_Api_Key=your_weather_api_key_here
```

## 📦 Installation

1. Clone the repository:
```bash
git clone https://github.com/berkucuk/tetra.git
cd tetra
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Make sure ChromeDriver is properly installed and available in your PATH or in the project directory.

4. Create the `.env` file with your API keys as described above.

## 🚀 Usage

Run the main application:
```bash
python linux-chan.py
```

### Core Functions

- **E-commerce Search**: Enter product descriptions or problems (like "My computer is running slowly") to get appropriate product recommendations
- **Weather Inquiry**: Ask about weather in a specific location (e.g., "What's the weather in Ankara today?")
- **Image Analysis**: Upload images for AI-powered analysis and description
- **Conversational AI**: Engage in natural conversations about various topics

## 📁 Project Structure

- **linux-chan.py**: Main application file that runs the GUI and integrates all components
- **hepsiburada_data_gether.py**: Module for searching and gathering product data from HepsiBurada
- **hepsiburada_buy.py**: Module for automating the product purchase process on HepsiBurada

## 🛠️ Configuration

- **Language**: Select from multiple supported languages in the dropdown menu
- **Voice Output**: Toggle voice output on/off as needed
- **Image Upload**: Use the "Upload Image" button to analyze images with AI

## 🤝 Contributing

Contributions to improve Tetra are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 Future Improvements

- Support for additional e-commerce platforms
- More advanced product comparison features
- User accounts and purchase history tracking
- Expanded language support
- Integration with other AI services and APIs

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- Google Gemini API for providing conversational AI capabilities
- WeatherAPI for weather data
- The Selenium and PyQt5 communities for excellent documentation

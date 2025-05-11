#!/usr/bin/env python3

import os
import sys
import logging
import re
import time
import xml.etree.ElementTree as ET
import io
import base64
from typing import Optional, Tuple, Union

import pygame
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from gtts import gTTS
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QComboBox, QTextEdit, QLineEdit, QPushButton,
                           QMessageBox, QGraphicsBlurEffect, QStackedLayout, 
                           QFileDialog, QSizePolicy)
from PyQt5.QtGui import QPixmap, QFont, QIcon, QImage
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QByteArray, QBuffer
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from PIL import Image

from hepsiburada_data_gether import hepsiburada_urunleri_incele
from hepsiburada_buy import open_url_with_webdriver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
language = "English"  # Default language
ICON_PATH = "./"
TEMP_VOICE_DIR = "temp_voice"
TEMP_IMAGE_DIR = "temp_image"

# Language mappings
PLACEHOLDER_TEXTS = {
    "English": "Type your message here...",
    "Turkish": "Mesajınızı buraya yazın...",
    "Spanish": "Escribe tu mensaje aquí...",
    "German": "Schreiben Sie Ihre Nachricht hier...",
    "French": "Écrivez votre message ici...",
    "Russian": "Введите ваше сообщение здесь..."
}

SEND_BUTTON_TEXTS = {
    "English": "Send",
    "Turkish": "Gönder",
    "Spanish": "Enviar",
    "German": "Senden",
    "French": "Envoyer",
    "Russian": "Отправить"
}

VOICE_SWITCH_TEXTS = {
    "English": "Voice: ",
    "Turkish": "Ses: ",
    "Spanish": "Voz: ",
    "German": "Stimme: ",
    "French": "Voix: ",
    "Russian": "Голос: "
}

IMAGE_BUTTON_TEXTS = {
    "English": "Upload Image",
    "Turkish": "Resim Yükle",
    "Spanish": "Subir Imagen",
    "German": "Bild Hochladen",
    "French": "Télécharger une Image",
    "Russian": "Загрузить Изображение"
}

VOICE_LANG_MAP = {
    "English": "en",
    "Turkish": "tr",
    "Spanish": "es",
    "German": "de",
    "French": "fr",
    "Russian": "ru"
}


def load_env_variables() -> Tuple[str, str]:
    """Load API keys from environment variables"""
    load_dotenv()
    gemini_api = os.getenv("Gemini_Api_Key")
    weather_api = os.getenv("Weather_Api_Key")

    if not gemini_api or not weather_api:
        raise ValueError("API keys not found in .env file :(")
    return gemini_api, weather_api


def play_voice(text: str, volume: float = 1.0, lang: str = "en"):
    """Generate and play text-to-speech audio"""
    # Create temp_voice directory if it doesn't exist
    if not os.path.exists(TEMP_VOICE_DIR):
        os.makedirs(TEMP_VOICE_DIR)

    voice_file = os.path.join(TEMP_VOICE_DIR, "voice.mp3")
    
    try:
        # Generate and save the speech file
        tts = gTTS(text, lang=lang)
        tts.save(voice_file)

        # Initialize pygame mixer
        pygame.mixer.init()

        # Load the audio file
        pygame.mixer.music.load(voice_file)

        # Set volume (0.0 to 1.0)
        pygame.mixer.music.set_volume(min(1.0, max(0.0, volume)))

        # Start playing
        pygame.mixer.music.play()

        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            time.sleep(0.01)

    except Exception as e:
        logger.error(f"Error playing voice: {e}")
    finally:
        # Cleanup
        pygame.quit()

        # Remove temporary file
        if os.path.exists(voice_file):
            os.remove(voice_file)


def save_temp_image(image_path: str) -> str:
    """Save a temporary copy of the uploaded image"""
    # Create temp image directory if it doesn't exist
    if not os.path.exists(TEMP_IMAGE_DIR):
        os.makedirs(TEMP_IMAGE_DIR)

    # Generate a unique filename based on timestamp
    filename = f"temp_image_{int(time.time())}{os.path.splitext(image_path)[1]}"
    temp_path = os.path.join(TEMP_IMAGE_DIR, filename)
    
    try:
        # Open and save the image using PIL for better compatibility
        img = Image.open(image_path)
        img.save(temp_path)
        return temp_path
    except Exception as e:
        logger.error(f"Error saving temporary image: {e}")
        return None


def encode_image_to_base64(image_path: str) -> Optional[str]:
    """Encode image to base64 for Gemini API"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding image: {e}")
        return None


class GeminiChatBot:
    """Gemini API wrapper to handle chat interactions"""
    
    def __init__(self):
        self.api_key, _ = load_env_variables()
        self._initialize_model()

    def _initialize_model(self):
        """Configure the Gemini API with API key"""
        genai.configure(api_key=self.api_key)
        
    def process_request(self, user_input: str, system_prompt: str) -> Optional[str]:
        """
        Process a text-only request using the Gemini model
        
        Args:
            user_input: The user's input text
            system_prompt: The system prompt to guide the model
            
        Returns:
            Optional[str]: The model's response or None if an error occurred
        """
        try:
            # Create a ChatGoogleGenerativeAI instance using langchain
            model = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=self.api_key,
                temperature=0
            )
            
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("user", "{user_input}")
            ])

            chain = prompt_template | model | StrOutputParser()
            result = chain.invoke({"user_input": user_input})
            return result

        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return None
    
    def process_image_request(self, user_input: str, image_path: str, system_prompt: str) -> Optional[str]:
        """
        Process a request containing both text and an image using the Gemini model
        
        Args:
            user_input: The user's input text
            image_path: Path to the image file
            system_prompt: The system prompt to guide the model
            
        Returns:
            Optional[str]: The model's response or None if an error occurred
        """
        try:
            # Create a direct Gemini model instance that can handle multimodal content
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Encode the image to base64
            image_data = encode_image_to_base64(image_path)
            if not image_data:
                return "Failed to process the image."
            
            # Combine system prompt with user input
            full_prompt = f"{system_prompt}\n\nUser Message: {user_input}"
            
            # Create parts for multimodal content
            parts = [
                {"text": full_prompt},
                {
                    "inline_data": {
                        "mime_type": f"image/{os.path.splitext(image_path)[1][1:].lower()}",
                        "data": image_data
                    }
                }
            ]
            
            # Generate content with image and text
            response = model.generate_content(parts, generation_config={"temperature": 0})
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error processing image request: {str(e)}")
            return f"Error processing image request: {str(e)}"


class ChatWorker(QThread):
    """Worker thread to handle AI requests in the background"""
    
    finished = pyqtSignal(tuple)
    error = pyqtSignal(str)

    def __init__(self, chat_bot, agent_type, user_input, image_path=None):
        super().__init__()
        self.chat_bot = chat_bot
        self.agent_type = agent_type
        self.user_input = user_input
        self.image_path = image_path

    def run(self):
        try:
            result = None
            if self.agent_type == "e_ticaret":
                result = e_ticaret(self.user_input, self.chat_bot)
                #item_selector(result, self.chat_bot)
            elif self.agent_type == "weather_gether":
                result = weather_gether(self.user_input, self.chat_bot)
            elif self.agent_type == "friend_chat":
                result = friend_chat(self.user_input, self.chat_bot)
            elif self.agent_type == "image_analysis":
                result = image_analysis(self.user_input, self.image_path, self.chat_bot)
                
            self.finished.emit((self.agent_type, result))
        except Exception as e:
            logger.error(f"Error in worker thread: {e}")
            self.error.emit(str(e))


def e_ticaret(user_input: str, chat_bot) -> dict:
    """Handle e-commerce product search requests"""
    system_prompt = f"""
        Sen, kullanıcının tarif ettiği problemi çözecek doğru donanım ürünü öneren bir asistansın.
        
        ÖNEMLİ KURALLAR:
        1. Sadece ve sadece ürün adını döndür, açıklama yapma - sadece arama için kullanılacak ürün adını ver.
        2. Hızla alakalı bir problem (bilgisayarın yavaş çalışması, geç açılması vb.) söz konusu olduğunda:
           - Kullanıcı HDD/Hard Disk Drive kullanıyorsa kesinlikle "SSD" öner
           - Kullanıcı bellek/RAM sorunlarından bahsediyorsa "RAM" veya "bellek" öner
           - Kullanıcı işlemci performansından bahsediyorsa "işlemci" veya "CPU" öner
        3. Bilgisayar yavaşlığı, programların geç açılması veya boot süresinin uzunluğu ile ilgili şikayetlerde
           varsayılan önerin her zaman "SSD" olmalıdır, başka bir şey değil.
        4. "Donanım hızlandırıcı" gibi belirsiz veya genel terimler kullanma, mutlaka "SSD", "RAM", "işlemci" gibi
           somut donanım parçaları belirt.
        
        Çıktı sadece aranacak ürün adı olmalıdır, mesela: "SSD", "DDR4 RAM", "Intel işlemci" gibi.
        Çıktı şu dilde olmalıdır: {language}
    """
    response = chat_bot.process_request(user_input, system_prompt)
    if not response:
        raise ValueError("No response from chat bot")
    
    logger.info(f"Product search term: {response}")
    urun_list = hepsiburada_urunleri_incele(response)    
    return urun_list


def item_selector(product_list: dict, chat_bot, user_input: str) -> str:
    """Select the best product from the search results and open it with WebDriver"""
    # Ürün listesinden URL'leri kaldırıp temiz bir JSON hazırla
    clean_product_list = {}
    for prod_id, prod_info in product_list.items():
        clean_product_list[prod_id] = {
            "urun_adi": prod_info.get("urun_adi", ""),
            "fiyat": prod_info.get("fiyat", ""),
            "marka": prod_info.get("marka", "")
        }
    
        system_prompt = f"""
        You are an expert assistant responsible for selecting the most reasonable and well-balanced product from a list, based on a deep analysis of product details.

        YOUR TASK:
        - Carefully examine and compare all product specifications, features, brand reputation, and price.
        - Select ONLY ONE product that offers the best combination of **quality**, **performance**, and **value** — not just the cheapest, but the smartest choice overall.

        DECISION CRITERIA:
        1. Think deeply and critically about each product's specifications, benefits, and trade-offs.
        2. Compare the products across all relevant factors before making your final decision.
        3. Prioritize **reliable brands**, **modern technologies**, and **practical features** that offer long-term value.

        USER'S REQUEST: "{user_input}"


        PRODUCT-SPECIFIC GUIDELINES:

        For SSDs:
        - Higher capacities (preferably 500GB or more) offer better long-term utility.
        - NVMe/M.2 drives are significantly faster and more efficient than SATA.
        - Reliable brands include Samsung, Kingston, Crucial, WD, and Corsair.

        For RAM:
        - Higher capacity (e.g., 16GB or 32GB) is better for multitasking and future-proofing.
        - Newer generation standards like DDR4 or DDR5 are preferable.
        - Higher MHz speed means better performance.
        - Dual-channel support is an advantage.

        For CPUs:
        - Prefer newer generations (e.g., Intel 11th/12th/13th gen or AMD Ryzen 5000/7000 series).
        - More cores and threads usually mean better multitasking and performance.
        - Higher base and boost clock speeds are important for responsiveness.
        - Integrated graphics can be an extra advantage depending on use case.

        EVALUATION PRINCIPLES:
        - Do not simply choose the lowest price — instead, choose the product that makes the most sense overall considering its features, performance, and long-term value.
        - Avoid overpriced products with weak specs, and avoid unreliable or unknown brands even if they are cheaper.
        - Choose the product that stands out as the most reasonable and well-rounded option after thorough analysis.

        RESPONSE FORMAT:
        Return ONLY the ID of the selected product (e.g., "product_3"). Do not provide any explanation—just the ID.

        Your response must be in this language: {language}
        """

    
    response = chat_bot.process_request(str(clean_product_list), system_prompt)
    
    if not response:
        logger.error("No response from product selector")
        return None
    
    # Strip any extra text, get just the product ID
    product_id = response.strip()
    
    # If the product exists in our original list, open its URL with WebDriver
    if product_id in product_list:
        selected_product = product_list[product_id]
        product_url = selected_product.get("urun_link", "")
        
        # Print the selected product URL to terminal (debugging için)
        print(f"\nSeçilen ürün: {product_id}")
        print(f"Ürün adı: {selected_product.get('urun_adi', 'Bilinmiyor')}")
        print(f"Fiyat: {selected_product.get('fiyat', 'Bilinmiyor')}")
        print(f"URL: {product_url}\n")
        
        # URL'yi WebDriver ile aç
        try:
            open_url_with_webdriver(product_url)
            logger.info(f"Ürün URL'si WebDriver ile açıldı: {product_url}")
        except Exception as e:
            logger.error(f"Ürün URL'si açılırken hata: {e}")
        
        logger.info(f"Selected product: {product_id}")
        return product_id
    else:
        logger.error(f"Selected product ID {product_id} not found in product list")
        return None


def weather_gether(user_input: str, chat_bot) -> str:
    """Get weather information for a requested location"""
    _, weather_api = load_env_variables()

    system_weather_prompt = f"""
    You are an advanced language model that extracts a single city name from the given text to be used for weather forecasts. Follow these instructions carefully:

    1. Extract exactly one city name from the text.
    2. If multiple city names are mentioned, return only the first one.
    3. If no city name is detected, return an error message in XML format.
    4. The output must be in well-formed XML format, following this structure:

    Valid Output Example:
    <weather_request>
        <city>CityName</city>
    </weather_request>

    Error Output Example:
    <weather_request>
        <error>No city name detected in the input text.</error>
    </weather_request>
    """
    response = chat_bot.process_request(user_input, system_weather_prompt)

    if not response:
        raise ValueError("No response from chat bot")
    
    try:
        # Clean the response to ensure proper XML formatting
        cleaned_data = re.sub(r'```', '', response)
        cleaned_data = re.sub(r'```xml', '', cleaned_data)
        cleaned_data = cleaned_data.strip()
        
        root = ET.fromstring(cleaned_data)
        city_element = root.find('city')
        
        if city_element is None:
            error_element = root.find('error')
            if error_element is not None:
                return f"Error: {error_element.text}"
            return "Error: Could not detect city name."
            
        location = city_element.text
    except Exception as e:
        logger.error(f"XML parsing error: {e}")
        return f"Error parsing city information: {e}"

    url = "https://api.weatherapi.com/v1/forecast.xml"
    days = 1

    try:
        response = requests.get(
            url,
            params={"key": weather_api, "q": location, "days": days},
            timeout=10
        )
        response.raise_for_status()

        root = ET.fromstring(response.content)
        location_name = root.find("location/name").text
        current_temp = root.find("current/temp_c").text
        current_weather = root.find("current/condition/text").text

        return f"Location: {location_name}, Temperature: {current_temp}°C, Weather: {current_weather}"

    except Exception as e:
        logger.error(f"Weather API error: {e}")
        raise


def friend_chat(user_input: str, chat_bot) -> str:
    """Handle casual conversation"""
    system_prompt = f"""
    You are an experienced AI assistant. Your role is to help users solve their problems using only existing resources, free methods, and tools they already have access to.

    Do **not** recommend paid services, subscriptions, or purchasing new products. Instead, provide creative, practical, and actionable solutions that do not require any additional cost.

    Your responses must always be in **{language}**, and they should be clear, concise, and step-by-step when necessary. You may suggest open-source software, free online tools, built-in system features, or manual methods that can help solve the issue.
    """

    response = chat_bot.process_request(user_input, system_prompt)
    if not response:
        raise ValueError("No response from chat bot")
    return response


def image_analysis(user_input: str, image_path: str, chat_bot) -> str:
    """Analyze the uploaded image and respond to the user's query"""
    system_prompt = f"""
    You are an advanced visual analysis assistant. You have been given an image to analyze along with a user query.
    
    Your task is to:
    1. Carefully examine the image in detail
    2. Respond to the user's question about the image
    3. If no specific question is asked, provide a thoughtful analysis of what is visible in the image
    4. Be specific and detailed about what you see, referencing specific elements in the image
    
    Important guidelines:
    - Be objective in your descriptions
    - Provide information that is directly visible in the image
    - If asked to read text in the image, transcribe it accurately
    - If the user is asking for specific objects or information that isn't visible in the image, politely let them know
    - If the image appears to be a technical diagram, error message, or computer screen, provide appropriate technical context
    
    Your response must be in the language: {language}
    """
    
    response = chat_bot.process_image_request(user_input, image_path, system_prompt)
    if not response:
        raise ValueError("No response from chat bot for image analysis")
    return response


def agent_selector(chat_bot, user_input: str, has_image: bool = False) -> str:
    """Select the appropriate agent based on the user's request"""
    if has_image:
        return "image_analysis"  # If image is present, always use image analysis agent
    
    system_prompt = """
    You are a task dispatcher. Select the most appropriate agent based on the user's request and return only the agent name as a response. Don't provide any other explanation, just specify the agent name.
    
    If the request is about buying or finding a product, select the 'e_ticaret' agent.
    If the request is about getting weather information, select the 'weather_gether' agent.
    If the request is about casual, friendly conversation, select the 'friend_chat' agent.
    """

    response = chat_bot.process_request(user_input, system_prompt)
    if not response:
        raise ValueError("No response from agent selector")
    return response.strip()


class ChatBotGUI(QWidget):
    """Main GUI class for the chatbot application"""
    
    def __init__(self):
        super().__init__()
        self.current_language = "English"
        self.voice_active = False  # Default voice state
        self.current_image_path = None  # Track the currently loaded image
        self.setWindowTitle('Tetra AI')
        self.setFixedSize(600, 1000)

        global language
        language = "English"  # Default language

        self.init_ui()
        try:
            self.chat_bot = GeminiChatBot()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize chat bot: {e}")
            sys.exit(1)

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Top Controls Layout
        top_controls = QHBoxLayout()

        # Language Selection
        self.setup_language_selector(top_controls)

        # Voice Switch
        self.setup_voice_switch(top_controls)

        layout.addLayout(top_controls)

        # Image
        self.setup_image(layout)

        # Chat Display
        self.setup_chat_display(layout)
        
        # Image Preview Area
        self.setup_image_preview(layout)

        # Input Area
        self.setup_input_area(layout)

        self.setLayout(layout)

    def setup_language_selector(self, layout):
        """Set up the language selection dropdown"""
        label = QLabel("Language/Dil:")
        label.setFont(QFont("Arial", 11, QFont.Bold))

        self.language_combo = QComboBox()
        self.language_combo.setFont(QFont("Arial", 11))
        self.language_combo.addItems([
            "English", "Turkish", "Spanish", "German", "French", "Russian"
        ])
        self.language_combo.currentTextChanged.connect(self.change_language)

        layout.addWidget(label)
        layout.addWidget(self.language_combo)
        layout.addStretch()

    def setup_voice_switch(self, layout):
        """Set up the voice activation switch"""
        voice_layout = QHBoxLayout()

        self.voice_label = QLabel(VOICE_SWITCH_TEXTS["English"])
        self.voice_label.setFont(QFont("Arial", 11, QFont.Bold))

        self.voice_combo = QComboBox()
        self.voice_combo.setFont(QFont("Arial", 11))
        self.voice_combo.addItems(["OFF", "ON"])
        self.voice_combo.setCurrentText("OFF")  # Default state
        self.voice_combo.currentTextChanged.connect(self.toggle_voice)
        self.voice_active = False
        voice_layout.addWidget(self.voice_label)
        voice_layout.addWidget(self.voice_combo)
        layout.addLayout(voice_layout)
        
    def toggle_voice(self, state):
        """Toggle voice mode on/off"""
        self.voice_active = (state == "ON")
        logger.info(f"Voice mode: {self.voice_active}")

    def setup_image(self, layout):
        """Set up the image display area"""
        # Load the photo
        pixmap = QPixmap(os.path.join(ICON_PATH, "/run/media/berkkucukk/Depo/WebDriver/tetra.png"))

        if not pixmap.isNull():
            # Daha küçük boyut kullanın, örneğin 300x240
            container_width = 300  # Orijinal: 500
            container_height = 240  # Orijinal: 400
            
            # Create container widget with QVBoxLayout for centering
            container = QWidget(self)
            container.setFixedSize(container_width, container_height)
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            
            # Create image container with stacked widget
            image_container = QWidget()
            image_container.setFixedSize(container_width, container_height)
            
            # --- Blurred background photo ---
            blur_label = QLabel(image_container)
            blurred_pixmap = pixmap.scaled(container_width, container_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            blur_label.setPixmap(blurred_pixmap)
            
            blur_effect = QGraphicsBlurEffect()
            blur_effect.setBlurRadius(20)  # Blur level
            blur_label.setGraphicsEffect(blur_effect)
            blur_label.setAlignment(Qt.AlignCenter)
            blur_label.setGeometry(0, 0, container_width, container_height)
            
            # --- Sharp foreground photo ---
            front_label = QLabel(image_container)
            front_pixmap = pixmap.scaled(container_width, container_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            front_label.setPixmap(front_pixmap)
            front_label.setAlignment(Qt.AlignCenter)
            
            # Calculate the center position for the front image
            img_width = front_pixmap.width()
            img_height = front_pixmap.height()
            x_pos = (container_width - img_width) // 2
            y_pos = (container_height - img_height) // 2
            front_label.setGeometry(x_pos, y_pos, img_width, img_height)
            
            # Add image container to the main container's layout
            container_layout.addWidget(image_container, 0, Qt.AlignCenter)
            
            # Add container to layout
            layout.addWidget(container, 0, Qt.AlignCenter)
        else:
            QMessageBox.warning(self, "Warning", "Failed to load image")
            
    def setup_chat_display(self, layout):
        """Set up the chat display area"""
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMinimumHeight(200)
        self.chat_display.setFont(QFont("Courier New", 11))
        layout.addWidget(self.chat_display)
        
    def setup_image_preview(self, layout):
        """Set up the image preview area (initially hidden)"""
        self.image_preview_container = QWidget()
        preview_layout = QVBoxLayout(self.image_preview_container)
        
        # Label to display the image preview
        self.image_preview_label = QLabel()
        self.image_preview_label.setAlignment(Qt.AlignCenter)
        self.image_preview_label.setMinimumHeight(150)
        self.image_preview_label.setMaximumHeight(200)
        self.image_preview_label.setStyleSheet("border: 1px solid #cccccc; background-color: #f0f0f0;")
        preview_layout.addWidget(self.image_preview_label)
        
        # Button to remove the image
        remove_layout = QHBoxLayout()
        remove_layout.addStretch()
        
        self.remove_image_button = QPushButton("✖ Remove Image")
        self.remove_image_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border-radius: 15px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.remove_image_button.clicked.connect(self.remove_image)
        remove_layout.addWidget(self.remove_image_button)
        
        preview_layout.addLayout(remove_layout)
        
        # Initially hide the image preview container
        self.image_preview_container.setVisible(False)
        
        layout.addWidget(self.image_preview_container)

    def setup_input_area(self, layout):
        """Set up the input text area and send button"""
        input_layout = QHBoxLayout()

        # Text input field
        self.entry = QLineEdit()
        self.entry.setFont(QFont("Arial", 12))
        self.entry.setPlaceholderText(PLACEHOLDER_TEXTS["English"])
        self.entry.returnPressed.connect(self.handle_request)

        # Image upload button
        self.image_button = QPushButton(IMAGE_BUTTON_TEXTS["English"])
        self.image_button.setFont(QFont("Arial", 11))
        self.image_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 15px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:pressed {
                background-color: #2E7D32;
            }
        """)
        self.image_button.clicked.connect(self.open_image_dialog)

        # Send button
        self.send_button = QPushButton(SEND_BUTTON_TEXTS["English"])
        self.send_button.setFont(QFont("Arial", 11))
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #4285F4;
                color: white;
                border-radius: 15px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3367D6;
            }
            QPushButton:pressed {
                background-color: #2850A7;
            }
        """)
        self.send_button.clicked.connect(self.handle_request)

        input_layout.addWidget(self.entry, stretch=3)
        input_layout.addWidget(self.image_button, stretch=1)
        input_layout.addWidget(self.send_button, stretch=1)
        layout.addLayout(input_layout)

    def change_language(self, new_language):
        """Change the application language"""
        global language
        self.current_language = new_language
        language = new_language

        # Update placeholder text and send button text based on selected language
        self.entry.setPlaceholderText(PLACEHOLDER_TEXTS.get(new_language, "Type your message here..."))
        self.send_button.setText(SEND_BUTTON_TEXTS.get(new_language, "Send"))
        self.voice_label.setText(VOICE_SWITCH_TEXTS.get(new_language, "Voice: "))
        self.image_button.setText(IMAGE_BUTTON_TEXTS.get(new_language, "Upload Image"))

    def open_image_dialog(self):
        """Open a file dialog to select an image"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Image", 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)",
            options=options
        )
        
        if file_path:
            self.load_image(file_path)
    
    def load_image(self, image_path):
        """Load and display the selected image"""
        try:
            # Create a temporary copy of the image
            temp_path = save_temp_image(image_path)
            if not temp_path:
                raise ValueError("Failed to save temporary image")
            
            # Load and display the image preview
            pixmap = QPixmap(temp_path)
            if pixmap.isNull():
                raise ValueError("Failed to load image")
            
            # Scale the image to fit the preview area while maintaining aspect ratio
            preview_width = self.image_preview_label.width()
            preview_height = self.image_preview_label.height()
            scaled_pixmap = pixmap.scaled(
                preview_width, 
                preview_height, 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            
            self.image_preview_label.setPixmap(scaled_pixmap)
            self.image_preview_container.setVisible(True)
            
            # Store the path to the temporary image
            self.current_image_path = temp_path
            
            logger.info(f"Image loaded: {image_path}")
            
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            QMessageBox.warning(self, "Image Error", f"Failed to load image: {e}")
            self.current_image_path = None
    
    def remove_image(self):
        """Remove the currently loaded image"""
        self.image_preview_label.clear()
        self.image_preview_container.setVisible(False)
        
        # Delete the temporary file if it exists
        if self.current_image_path and os.path.exists(self.current_image_path):
            try:
                os.remove(self.current_image_path)
            except Exception as e:
                logger.error(f"Error removing temporary image file: {e}")
        
        self.current_image_path = None
        logger.info("Image removed")

    def handle_request(self):
        """Process the user's request when send button is clicked"""
        user_input = self.entry.text().strip()
        has_image = self.current_image_path is not None
        
        if not user_input and not has_image:
            self.chat_display.append("[Error] Please enter a message or upload an image.")
            return

        self.send_button.setEnabled(False)
        self.entry.clear()
        
        # Add user message to chat display
        self.chat_display.append(f"You: {user_input}")
        if has_image:
            self.chat_display.append("[Image uploaded]")
        self.chat_display.append("")  # Extra line for spacing

        try:
            # Determine which agent to use based on user input and presence of image
            agent_type = agent_selector(self.chat_bot, user_input, has_image)
            
            # Show appropriate loading message immediately based on agent type
            if agent_type == "e_ticaret":
                self.chat_display.append("Tetra AI: Searching Hepsiburada...\n")
            elif agent_type == "weather_gether":
                self.chat_display.append("Tetra AI: Fetching weather information...\n")
            elif agent_type == "image_analysis":
                self.chat_display.append("Tetra AI: Analyzing your image...\n")
            else:
                self.chat_display.append("Tetra AI: Processing your request...\n")
            
            # Create worker thread with image path if available
            self.worker = ChatWorker(self.chat_bot, agent_type, user_input, self.current_image_path)
            self.worker.finished.connect(self.handle_response)
            self.worker.error.connect(self.handle_error)
            self.worker.start()

        except Exception as e:
            self.handle_error(str(e))

    def handle_response(self, result):
        """Handle the response from the AI"""
        agent_type, response = result
        
        if agent_type == "e_ticaret":
            # Don't display "Searching Hepsiburada..." again since it's already shown
            if isinstance(response, dict) and response:
                # Get original user input (this is passed to the ChatWorker)
                original_user_input = self.worker.user_input
                
                # Select the most appropriate product based on user's request
                selected_product_id = item_selector(response, self.chat_bot, original_user_input)
                
                # If a product is selected, highlight it in the display
                if selected_product_id and selected_product_id in response:
                    selected_product = response[selected_product_id]
                    response_text = "İşte sorunun için önerdiğim en iyi ürün:\n\n"
                    response_text += f"➤ {selected_product.get('urun_adi', 'Bilinmiyor')}\n"
                    response_text += f"  Fiyat: {selected_product.get('fiyat', 'N/A')}\n\n"
                    
                    response_text += "Diğer alternatifler:\n"
                    for prod_id, prod_info in response.items():
                        if prod_id != selected_product_id:  # Don't list the selected product again
                            response_text += f"• {prod_info.get('urun_adi', 'Bilinmiyor')}\n"
                            response_text += f"  Fiyat: {prod_info.get('fiyat', 'N/A')}\n"
                            response_text += "\n"
                else:
                    # If no product is selected, list all products
                    response_text = "İşte bulduğum ürünler:\n\n"
                    for prod_id, prod_info in response.items():
                        response_text += f"• {prod_info.get('urun_adi', 'Bilinmiyor')}\n"
                        response_text += f"  Fiyat: {prod_info.get('fiyat', 'N/A')}\n"
                        response_text += "\n"
            else:
                response_text = "Üzgünüm, herhangi bir ürün bulamadım."
                
            self.chat_display.append(f"Tetra AI: {response_text}\n")
            voice_text = "İhtiyacınıza uygun ürünleri buldum. Detaylar sohbet penceresinde."
                
        elif agent_type == "weather_gether":
            self.chat_display.append(f"Tetra AI: {response}\n")
            voice_text = response
                
        elif agent_type == "friend_chat":
            self.chat_display.append(f"Tetra AI: {response}\n")
            voice_text = response
            
        elif agent_type == "image_analysis":
            self.chat_display.append(f"Tetra AI: {response}\n")
            voice_text = "Image analysis completed. Check the chat window for details."
            
            # Remove the image after analysis is complete
            self.remove_image()
            
        else:
            self.chat_display.append(f"Linux Chan: Bu tür istekleri nasıl işleyeceğimden emin değilim.\n")
            voice_text = "Bu tür istekleri nasıl işleyeceğimden emin değilim."

        # Only play voice if voice_active is True
        if self.voice_active:
            play_voice(
                text=voice_text,
                volume=0.5,
                lang=VOICE_LANG_MAP.get(language, "en")
            )

        self.send_button.setEnabled(True)
        
    def handle_error(self, error_message):
        """Handle errors that occur during processing"""
        self.chat_display.append(f"[Error] {error_message}\n")
        self.send_button.setEnabled(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('/run/media/berkkucukk/Depo/WebDriver/tetra.png'))

    # Create temp directories if they don't exist
    os.makedirs(TEMP_VOICE_DIR, exist_ok=True)
    os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)

    try:
        window = ChatBotGUI()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"Application crashed: {e}")
        QMessageBox.critical(None, "Fatal Error", f"Application crashed: {e}")
        sys.exit(1)
import telebot
from telebot.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
import json

# आपका टोकन और वेब-ऐप लिंक (मैंने सेट कर दिया है)
BOT_TOKEN = "8724525159:AAEN3QxLde5AeInJ5maG2P0Wy7yKuq8gjgS"
WEBAPP_URL = "https://jigur968-stac.github.io/fit-india-ai-bot/index.html"

bot = telebot.TeleBot(BOT_TOKEN)

# Phase 1: Data Logging (यूज़र का डेटा सेव करने के लिए एक डिक्शनरी)
user_database = {}

@bot.message_handler(commands=['start'])
def start_message(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    web_app_button = KeyboardButton(text="💪 अपनी प्रोफाइल बनाएं", web_app=WebAppInfo(url=WEBAPP_URL))
    markup.add(web_app_button)
    
    bot.send_message(message.chat.id, f"नमस्ते {message.from_user.first_name}! 🏋️‍♂️ Fit India AI में आपका स्वागत है। शुरू करने के लिए नीचे दिए गए बटन पर क्लिक करें:", reply_markup=markup)

@bot.message_handler(content_types=['web_app_data'])
def handle_webapp_data(message):
    try:
        # वेब-ऐप से आया डेटा पढ़ना
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        
        # Phase 1: Data Logging (डेटाबेस में सेव करना)
        user_database[user_id] = data
        
        name = data.get('name')
        medical_condition = data.get('medical')
        
        # Phase 1: Medical Safeguard Filter
        if medical_condition == "Yes":
            response = f"⚠️ {name}, चूंकि आपने बताया है कि आपको मेडिकल समस्या है, इसलिए हमारा AI कस्टमाइज्ड डाइट प्लान देने से पहले आपको अपने डॉक्टर या डायटीशियन से सलाह लेने की सख्त हिदायत देता है। स्वास्थ्य सबसे पहले है! 🙏"
        else:
            response = f"🎉 बहुत बढ़िया {name}! आपका डेटा सुरक्षित रूप से सेव कर लिया गया है।\n\n📊 आपकी प्रोफाइल:\nउम्र: {data.get('age')}\nहाइट: {data.get('height')} cm\nवजन: {data.get('weight')} kg\nलक्ष्य: {data.get('goal')}\n\n✅ Phase 1 पूरा हुआ! जल्द ही हम आपके लिए कस्टमाइज्ड डाइट और वर्कआउट (Phase 2) शुरू करेंगे।"

        bot.send_message(message.chat.id, response)
        
    except Exception as e:
        bot.send_message(message.chat.id, "❌ कुछ गड़बड़ हो गई। कृपया फिर से कोशिश करें।")

print("Bot is running Phase 1...")
bot.infinity_polling()

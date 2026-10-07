import telebot
from telebot.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
import json

# अपना टेलीग्राम बॉट टोकन यहाँ डालें (हम इसे बाद में BotFather से लेकर अपडेट करेंगे)
BOT_TOKEN = "8724525159:AAHbuSVs1GzQU2y6ImQmnU025DgtovSBGTs"
# यह लिंक गिटहब पेजेस का होगा, जिसे हम अगले स्टेप में जनरेट करेंगे
WEBAPP_URL = "https://jigur968-stack.github.io/fit-india-ai-bot/index.html"

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start_message(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    # यह बटन दबाते ही आपका वेब-फॉर्म (index.html) खुलेगा
    web_app_button = KeyboardButton(text="📝 अपनी प्रोफाइल बनाएं", web_app=WebAppInfo(url=WEBAPP_URL))
    markup.add(web_app_button)
    
    bot.send_message(
        message.chat.id,
        f"नमस्ते {message.from_user.first_name}! 🚀\nFit India AI में आपका स्वागत है।\nअपना कस्टमाइज्ड डाइट और वर्कआउट प्लान पाने के लिए नीचे दिए गए बटन पर क्लिक करें:",
        reply_markup=markup
    )

@bot.message_handler(content_types=['web_app_data'])
def handle_webapp_data(message):
    # वेब-फॉर्म से सबमिट किया गया डेटा यहाँ आएगा
    data = json.loads(message.web_app_data.data)
    
    response_text = (
        f"आपका डेटा सफलतापूर्वक सेव हो गया है! ✅\n\n"
        f"👤 नाम: {data['name']}\n"
        f"🎂 उम्र: {data['age']}\n"
        f"🚻 जेंडर: {data['gender']}\n"
        f"📏 हाइट: {data['height']} cm\n"
        f"⚖️ वजन: {data['weight']} kg\n"
        f"🎯 लक्ष्य: {data['goal']}\n\n"
        f"हम जल्द ही आपका डेटा एनालाइज करके आपका पहला डाइट चार्ट भेजेंगे! 💪"
    )
    # कीबोर्ड को हटाने के लिए
    remove_keyboard = telebot.types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, response_text, reply_markup=remove_keyboard)

if __name__ == "__main__":
    print("Fit India AI Bot चालू हो गया है...")
    bot.infinity_polling()


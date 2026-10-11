import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, WebAppInfo
import json
import sqlite3
import os
import time
import google.generativeai as genai
from PIL import Image
from io import BytesIO
from flask import Flask
import threading

# --- RENDER WEB SERVER SETUP (रेंडर हेल्थ चेक के लिए) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Fit India AI Bot is running smoothly on Render! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
# --------------------------------------------------------

# Environment Variables से Tokens उठाना (रेंडर डैशबोर्ड से आएंगे)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    print("Error: Tokens नहीं मिले! कृपया Render Environment Variables चेक करें।")
    exit()

# Google Gemini AI सेटअप
genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel('gemini-flash-latest')

bot = telebot.TeleBot(BOT_TOKEN)

# GitHub URL (Version 16)
WEBAPP_URL = "https://jigur968-stack.github.io/fit-india-ai-bot/index.html?v=16"

# डेटाबेस सेटअप
def setup_database():
    conn = sqlite3.connect('fitindia.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT, age INTEGER, gender TEXT,
            height REAL, weight REAL, goal TEXT, 
            diet TEXT, medical TEXT
        )
    ''')
    conn.commit()
    conn.close()

setup_database()

# लंबी चैट/मैसेज को टुकड़ों में भेजने का सेफ फंक्शन
def send_long_message(chat_id, text):
    if len(text) <= 4000:
        bot.send_message(chat_id, text, disable_web_page_preview=True, reply_markup=ReplyKeyboardRemove())
    else:
        for i in range(0, len(text), 4000):
            bot.send_message(chat_id, text[i:i+4000], disable_web_page_preview=True, reply_markup=ReplyKeyboardRemove())

# AI से डाइट प्लान बनवाने का फ़ंक्शन
def generate_ai_diet_plan(name, age, gender, height, weight, goal, diet):
    prompt = f"""
    आप Fit India AI के एक एक्सपर्ट डाइटिशियन और न्यूट्रिशनिस्ट हैं।
    यूज़र की प्रोफाइल:
    - नाम: {name}
    - उम्र: {age} वर्ष
    - लिंग: {gender}
    - ऊंचाई: {height} cm
    - वजन: {weight} kg
    - लक्ष्य (Goal): {goal}
    - भोजन प्राथमिकता (Diet Preference): {diet}

    कृपया यूज़र के लिए एक सुंदर, साफ और आसान हिंदी (Hinglish mix) में डाइट प्लान बनाएं।
    विशेष निर्देश: यूज़र की डाइट प्राथमिकता '{diet}' है।

    इसमें शामिल करें:
    1. 🎯 रोज़ाना की अनुमानित कैलोरी और प्रोटीन की आवश्यकता।
    2. 🥗 1-दिन का आसान भारतीय डाइट चार्ट (सुबह का नाश्ता, दोपहर का खाना, शाम का स्नैक, रात का खाना)।
    3. ✅ क्या खाएं और ❌ किससे परहेज करें।
    4. 💡 2-3 महत्वपूर्ण फिटनेस टिप्स।

    उत्तर को साफ-सुथरा और पॉइंट-बाय-पॉइंट रखें।
    """
    try:
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("Gemini AI Error:", e)
        return f"नमस्ते {name}! आपका डेटा सेव हो गया है। AI डाइट चार्ट जनरेट करने में थोड़ा समय लग रहा है।"

# AI से वर्कआउट प्लान बनवाने का फ़ंक्शन
def generate_ai_workout_plan(name, goal, gender):
    prompt = f"""
    आप Fit India AI के एक एक्सपर्ट फिटनेस कोच और ट्रेनर हैं।
    यूज़र की प्रोफाइल:
    - नाम: {name}
    - लिंग: {gender}
    - लक्ष्य (Goal): {goal}

    कृपया यूज़र के लिए 5-दिन का एक शानदार, साफ और आसान हिंदी (Hinglish mix) में होम/जिम वर्कआउट रूटीन बनाएं।
    विशेष निर्देश:
    1. हर दिन के वर्कआउट में मुख्य एक्सरसाइज के नाम दें।
    2. हर प्रमुख एक्सरसाइज के साथ उसका सही फॉर्म सीखने के लिए एक Markdown YouTube सर्च लिंक अवश्य जोड़ें।
    3. वार्म-अप और कूल-डाउन के टिप्स दें।
    """
    try:
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("Gemini AI Workout Error:", e)
        return f"नमस्ते {name}! वर्कआउट प्लान जनरेट करने में थोड़ा समय लग रहा है।"

# AI विज़न से खाने की फोटो और कैप्शन एनालाइज करने का फंक्शन
def analyze_meal_photo(image_bytes, caption, name, goal, diet):
    image = Image.open(BytesIO(image_bytes))
    user_note = f"यूज़र का नोट/कैप्शन: '{caption}'" if caption else "यूज़र ने कोई कैप्शन नहीं लिखा है।"
    
    prompt = f"""
    आप Fit India AI के एक एक्सपर्ट न्यूट्रिशनिस्ट और डाइटिशियन हैं।
    यूज़र की प्रोफाइल:
    - नाम: {name}
    - लक्ष्य (Goal): {goal}
    - भोजन प्राथमिकता (Diet Preference): {diet}
    - {user_note}

    महत्वपूर्ण निर्देश:
    1. सबसे पहले फोटो को अपनी आँखों (Vision) से खुद ध्यान से देखकर पहचानें कि उसमें कौन सा खाद्य पदार्थ (Food item) है। कैप्शन को कभी भी फूड के नाम की तरह कॉपी न करें।
    2. यूज़र के कैप्शन का उपयोग केवल मात्रा (Quantity) या संख्या समझने के लिए करें।
    3. फोटो में दिख रहे भोजन के अनुसार अनुमानित कैलोरी और मैक्रोज़ (Protein, Carbs, Fats) बताएं।
    4. क्या यह यूज़र के लक्ष्य ({goal}) और डाइट ({diet}) के हिसाब से सही है या नहीं, और सुधार के लिए सुझाव दें।
    
    उत्तर को साफ-सुथरा और पॉइंट-बाय-पॉइंट हिंदी (Hinglish mix) में रखें।
    """
    try:
        response = ai_model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        print("Gemini Vision AI Error:", e)
        return "तस्वीर का विश्लेषण करने में कुछ दिक्कत आई। कृपया साफ फोटो दोबारा भेजें।"

# AI टेक्स्ट चैट Q&A का फंक्शन
def generate_ai_text_reply(name, age, gender, height, weight, goal, diet, user_query):
    prompt = f"""
    आप Fit India AI के एक स्मार्ट, दोस्ताना और एक्सपर्ट फिटनेस कोच और न्यूट्रिशनिस्ट हैं।
    यूज़र की प्रोफाइल:
    - नाम: {name}
    - उम्र: {age} वर्ष
    - लिंग: {gender}
    - ऊंचाई: {height} cm
    - वजन: {weight} kg
    - लक्ष्य (Goal): {goal}
    - भोजन प्राथमिकता (Diet Preference): {diet}

    यूज़र का सवाल/संदेश: "{user_query}"

    कृपया यूज़र के इस सवाल का एक सटीक, मददगार और प्रेरणादायक जवाब हिंदी (Hinglish mix) में दें।
    """
    try:
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("Gemini Text AI Error:", e)
        return f"नमस्ते {name}! आपके सवाल का जवाब देने में थोड़ी तकनीकी समस्या आ रही है, कृपया दोबारा प्रयास करें।"

# स्टार्ट कमांड (डाइनेमिक बटन लॉजिक के साथ)
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    conn = sqlite3.connect('fitindia.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    if not user:
        markup.add(KeyboardButton("Create Profile 📝", web_app=WebAppInfo(url=WEBAPP_URL)))
    markup.add(KeyboardButton("Get Workout Routine 🏋️‍♂️"))
    
    greeting = f"नमस्ते {user[0]} जी!" if user else "Fit India AI में आपका स्वागत है! 🇮🇳"
    bot.send_message(
        message.chat.id, 
        f"{greeting}\nनीचे दिए गए बटन्स का उपयोग करें:", 
        reply_markup=markup
    )

# वर्कआउट कमांड और बटन हैंडलर
@bot.message_handler(commands=['workout'])
def workout_command(message):
    user_id = message.chat.id
    conn = sqlite3.connect('fitindia.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, goal, gender FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        name, goal, gender = user
        bot.send_chat_action(message.chat.id, 'typing')
        bot.send_message(message.chat.id, f"🤖 {name}, आपके गोल ({goal}) के अनुसार 5-दिन का कस्टमाइज्ड वर्कआउट प्लान तैयार किया जा रहा है... ⏳", reply_markup=ReplyKeyboardRemove())
        workout_plan = generate_ai_workout_plan(name, goal, gender)
        send_long_message(message.chat.id, workout_plan)
    else:
        bot.send_message(message.chat.id, "⚠️ पहले कृपया 'Create Profile 📝' बटन पर क्लिक करके अपनी प्रोफाइल बनाएं!")

@bot.message_handler(func=lambda message: message.text == "Get Workout Routine 🏋️‍♂️")
def workout_button_handler(message):
    workout_command(message)

# वेब ऐप से डेटा रिसीव करना
@bot.message_handler(content_types=['web_app_data'])
def receive_web_app_data(message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.chat.id
        
        conn = sqlite3.connect('fitindia.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, name, age, gender, height, weight, goal, diet, medical)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, data['name'], data['age'], data['gender'], data['height'], data['weight'], data['goal'], data['diet'], data['medical']))
        conn.commit()
        conn.close()

        if data['medical'] == 'Yes':
            response_text = f"नमस्ते {data['name']}! आपका डेटा सेव हो गया है। ⚠️\n\nचूँकि आपने मेडिकल कंडीशन 'Yes' चुनी है, इसलिए कोई भी सख्त डाइट या वर्कआउट शुरू करने से पहले कृपया अपने डॉक्टर से सलाह ज़रूर लें।"
            bot.send_message(message.chat.id, response_text, reply_markup=ReplyKeyboardRemove())
        else:
            bot.send_chat_action(message.chat.id, 'typing')
            bot.send_message(
                message.chat.id, 
                f"नमस्ते {data['name']}! आपकी प्रोफाइल सेव हो गई है। 🎉\n\n🤖 Fit India AI आपके डेटा और '{data['diet']}' डाइट के अनुसार आपका AI डाइट चार्ट तैयार कर रहा है... ⏳", 
                reply_markup=ReplyKeyboardRemove()
            )
            
            ai_diet_plan = generate_ai_diet_plan(
                data['name'], data['age'], data['gender'], 
                data['height'], data['weight'], data['goal'], data['diet']
            )
            
            send_long_message(message.chat.id, ai_diet_plan)
        
    except Exception as e:
        bot.send_message(message.chat.id, "डेटा सेव करने में कुछ दिक्कत आई। कृपया दोबारा प्रयास करें।", reply_markup=ReplyKeyboardRemove())
        print("Error:", e)

# फोटो हैंडलर
@bot.message_handler(content_types=['photo'])
def handle_photo_message(message):
    user_id = message.chat.id
    conn = sqlite3.connect('fitindia.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, goal, diet FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        name, goal, diet = user
        caption = message.caption if message.caption else ""
        bot.send_chat_action(message.chat.id, 'typing')
        bot.send_message(message.chat.id, f"📸 {name}, आपकी फूड फोटो मिल गई है! AI इसे और आपके नोट ('{caption}') को स्कैन करके सही कैलोरी का हिसाब लगा रहा है... ⏳")
        
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            analysis_result = analyze_meal_photo(downloaded_file, caption, name, goal, diet)
            send_long_message(message.chat.id, analysis_result)
        except Exception as e:
            print("Photo processing error:", e)
            bot.send_message(message.chat.id, "⚠️ फोटो प्रोसेस करने में दिक्कत आई। कृपया दोबारा प्रयास करें।")
    else:
        bot.send_message(message.chat.id, "⚠️ पहले कृपया 'Create Profile 📝' बटन पर क्लिक करके अपनी प्रोफाइल बनाएं!")

# स्मार्ट टेक्स्ट Q&A चैट हैंडलर
@bot.message_handler(func=lambda message: True)
def handle_all_text_messages(message):
    user_id = message.chat.id
    user_query = message.text
    
    conn = sqlite3.connect('fitindia.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, age, gender, height, weight, goal, diet FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        name, age, gender, height, weight, goal, diet = user
        bot.send_chat_action(message.chat.id, 'typing')
        reply_text = generate_ai_text_reply(name, age, gender, height, weight, goal, diet, user_query)
        send_long_message(message.chat.id, reply_text)
    else:
        bot.send_message(message.chat.id, "⚠️ कृपया पहले 'Create Profile 📝' बटन पर क्लिक करके अपनी प्रोफाइल बनाएं!")

# --- MAIN ENTRY POINT (रेंडर के लिए थ्रेडिंग और पोलिंग) ---
if __name__ == '__main__':
    print("Starting Telegram Bot on Render...")
    # बॉट को बैकग्राउंड थ्रेड में चलाना
    bot_thread = threading.Thread(target=run_flask)
    bot_thread.daemon = True
    bot_thread.start()

    # पोलिंग लूप
    while True:
        try:
            print("Bot polling started...")
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Connection lost ({e}). Retrying in 5 seconds...")
            time.sleep(5)

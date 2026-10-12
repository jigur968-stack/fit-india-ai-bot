import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, WebAppInfo
import json
import os
import time
import requests
import google.generativeai as genai
from PIL import Image
from io import BytesIO
from flask import Flask
import threading

# --- RENDER WEB SERVER SETUP (रेंडर हेल्थ चेक के लिए) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Fit India AI Bot is running smoothly with Supabase on Render! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
# --------------------------------------------------------

# Environment Variables से Tokens और Supabase Credentials उठाना
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: आवश्यक टोकन या Supabase Credentials नहीं मिले! कृपया Render Environment Variables चेक करें।")
    exit()

# Supabase REST API Headers
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Google Gemini AI सेटअप
genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel('gemini-flash-latest')

bot = telebot.TeleBot(BOT_TOKEN)

# GitHub URL (Version 16)
WEBAPP_URL = "https://jigur968-stack.github.io/fit-india-ai-bot/index.html?v=16"

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
    आप Fit India AI के एक्सपर्ट न्यूट्रिशनिस्ट हैं।
    प्रोफाइल: {name}, {age}वर्ष, {gender}, {height}cm, {weight}kg, Goal: {goal}, Diet: {diet}.

    संक्षिप्त, साफ और तेज हिंदी (Hinglish mix) में उत्तर दें:
    1. 🎯 दैनिक कैलोरी और प्रोटीन आवश्यकता।
    2. 🥗 1-दिन का आसान भारतीय डाइट चार्ट (नाश्ता, दोपहर, शाम, रात)।
    3. ✅ क्या खाएं और ❌ परहेज।
    4. 💡 2 मुख्य टिप्स।
    """
    try:
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("Gemini AI Error:", e)
        return f"नमस्ते {name}! आपकी प्रोफाइल सेव हो गई है।"

# AI से वर्कआउट प्लान बनवाने का फ़ंक्शन
def generate_ai_workout_plan(name, goal, gender):
    prompt = f"""
    आप Fit India AI के एक्सपर्ट फिटनेस कोच हैं।
    प्रोफाइल: {name}, {gender}, Goal: {goal}.

    संक्षिप्त हिंदी (Hinglish mix) में 5-दिन का होम/जिम वर्कआउट रूटीन बनाएं:
    - मुख्य एक्सरसाइज के नाम और Markdown YouTube सर्च लिंक दें।
    - वार्म-अप / कूल-डाउन टिप।
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
    user_note = f"नोट: '{caption}'" if caption else ""
    
    prompt = f"""
    आप Fit India AI के एक्सपर्ट न्यूट्रिशनिस्ट हैं।
    प्रोफाइल: {name}, Goal: {goal}, Diet: {diet}. {user_note}

    निर्देश:
    1. फोटो में फूड आइटम को स्वयं पहचानें।
    2. अनुमानित कैलोरी और मैक्रोज़ (Protein, Carbs, Fats) बताएं।
    3. यूज़र के लक्ष्य ({goal}) के अनुसार छोटा सुझाव दें।
    """
    try:
        response = ai_model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        print("Gemini Vision AI Error:", e)
        return "तस्वीर का विश्लेषण करने में कुछ दिक्कत आई। कृपया साफ फोटो दोबारा भेजें।"

# AI टेक्स्ट चैट Q&A का फंक्शन (डिजिटल दोस्त + माफी + शॉर्ट रिस्पॉन्स लॉजिक के साथ)
def generate_ai_text_reply(name, age, gender, height, weight, goal, diet, user_query):
    prompt = f"""
    आप Fit India AI के स्मार्ट, दोस्ताना और विनम्र फिटनेस कोच ('डिजिटल दोस्त') हैं।
    प्रोफाइल: {name}, {age}वर्ष, {gender}, Goal: {goal}, Diet: {diet}.
    यूज़र का सवाल/संदेश: "{user_query}"

    सख्त निर्देश (Strict Rules):
    1. जवाब बहुत छोटा, पॉइंट-टू-पॉइंट और केवल 3-4 पंक्तियों (Lines) में दें। बड़े पैराग्राफ बिल्कुल न लिखें ताकि यूज़र को पढ़ने में बोरियत (कंटाला) न हो।
    2. अगर यूज़र आपके पिछले जवाब की किसी गलती (जैसे कैलोरी, मात्रा या गिनती) को सुधार रहा है, तो बिना झिझक के तुरंत शालीनता से माफी मांगें (जैसे: "अरे! माफ कीजिएगा, मुझसे गिनती/पहचान में चूक हो गई..." या "क्षमा करें, आपकी बात बिल्कुल सही है...")।
    3. इसके बाद यूज़र के सुधार के अनुसार सही जानकारी दें।
    4. बातचीत को दिलचस्प और एंगेजिंग बनाने के लिए अंत में एक छोटा सा प्रासंगिक सवाल पूछें।
    5. आसान हिंदी (Hinglish mix) और उपयुक्त Emojis का उपयोग करें।
    """
    try:
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("Gemini Text AI Error:", e)
        return f"नमस्ते {name}! आपके सवाल का जवाब देने में तकनीकी समस्या आ रही है।"

# स्टार्ट कमांड (स्मार्ट वेलकम + डायनामिक बटन लॉजिक)
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    user_name = None
    
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?user_id=eq.{user_id}&select=name",
            headers=SUPABASE_HEADERS
        )
        if response.status_code == 200:
            data = response.json()
            if data:
                user_name = data[0].get('name')
    except Exception as e:
        print("Supabase fetch error in start:", e)
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    
    # अगर नया यूजर है - सिर्फ प्रोफाइल बनाने का बटन
    if not user_name:
        markup.add(KeyboardButton("Create Profile 📝", web_app=WebAppInfo(url=WEBAPP_URL)))
        text_message = "Fit India AI में आपका स्वागत है! 🇮🇳\n\nकृपया अपनी फिटनेस प्रोफाइल बनाने के लिए नीचे दिए गए 'Create Profile 📝' बटन पर क्लिक करें:"
    # अगर पुराना यूजर है - Create Profile का बटन गायब, सीधे ऑप्शंस मिलेंगे
    else:
        markup.add(KeyboardButton("Get Workout Routine 🏋️‍♂️"))
        text_message = f"नमस्ते {user_name} जी! Fit India AI में आपका स्वागत है। 🇮🇳\n\nआप मुझसे डाइट, वर्कआउट या कैलोरी से जुड़ा कोई भी सवाल पूछ सकते हैं या नीचे दिए बटन का उपयोग कर सकते हैं:"
    
    bot.send_message(
        message.chat.id, 
        text_message, 
        reply_markup=markup
    )

# वर्कआउट कमांड और बटन हैंडलर
@bot.message_handler(commands=['workout'])
def workout_command(message):
    user_id = message.chat.id
    user_data = None
    
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?user_id=eq.{user_id}&select=name,goal,gender",
            headers=SUPABASE_HEADERS
        )
        if response.status_code == 200 and response.json():
            user_data = response.json()[0]
    except Exception as e:
        print("Supabase fetch error in workout:", e)
    
    if user_data:
        name = user_data.get('name')
        goal = user_data.get('goal')
        gender = user_data.get('gender')
        
        bot.send_chat_action(message.chat.id, 'typing')
        bot.send_message(message.chat.id, f"🤖 {name}, आपके गोल ({goal}) के अनुसार 5-दिन का वर्कआउट प्लान तैयार किया जा रहा है... ⏳", reply_markup=ReplyKeyboardRemove())
        workout_plan = generate_ai_workout_plan(name, goal, gender)
        send_long_message(message.chat.id, workout_plan)
    else:
        bot.send_message(message.chat.id, "⚠️ पहले कृपया 'Create Profile 📝' बटन पर क्लिक करके अपनी प्रोफाइल बनाएं!")

@bot.message_handler(func=lambda message: message.text == "Get Workout Routine 🏋️‍♂️")
def workout_button_handler(message):
    workout_command(message)

# वेब ऐप से डेटा रिसीव करके Supabase में सेव करना
@bot.message_handler(content_types=['web_app_data'])
def receive_web_app_data(message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.chat.id
        
        payload = {
            "user_id": user_id,
            "name": data['name'],
            "age": data['age'],
            "gender": data['gender'],
            "height": data['height'],
            "weight": data['weight'],
            "goal": data['goal'],
            "diet": data['diet'],
            "medical": data['medical']
        }
        
        headers = SUPABASE_HEADERS.copy()
        headers["Prefer"] = "resolution=merge-duplicates"
        
        res = requests.post(f"{SUPABASE_URL}/rest/v1/users", headers=headers, json=payload)
        
        if res.status_code in [200, 201, 204]:
            if data['medical'] == 'Yes':
                response_text = f"नमस्ते {data['name']}! आपकी प्रोफाइल सेव हो गई है। ⚠️\n\nचूँकि आपने मेडिकल कंडीशन 'Yes' चुनी है, इसलिए कोई भी सख्त डाइट या वर्कआउट शुरू करने से पहले डॉक्टर से सलाह ज़रूर लें।"
                bot.send_message(message.chat.id, response_text, reply_markup=ReplyKeyboardRemove())
            else:
                bot.send_chat_action(message.chat.id, 'typing')
                bot.send_message(
                    message.chat.id, 
                    f"नमस्ते {data['name']}! आपकी प्रोफाइल सुरक्षित सेव हो गई है। 🎉\n\n🤖 Fit India AI आपके लिए AI डाइट चार्ट तैयार कर रहा है... ⏳", 
                    reply_markup=ReplyKeyboardRemove()
                )
                
                ai_diet_plan = generate_ai_diet_plan(
                    data['name'], data['age'], data['gender'], 
                    data['height'], data['weight'], data['goal'], data['diet']
                )
                
                send_long_message(message.chat.id, ai_diet_plan)
        else:
            print("Supabase Save Error:", res.text)
            bot.send_message(message.chat.id, "डेटा सेव करने में दिक्कत आई। कृपया दोबारा प्रयास करें।", reply_markup=ReplyKeyboardRemove())
        
    except Exception as e:
        bot.send_message(message.chat.id, "डेटा प्रोसेस करने में दिक्कत आई। कृपया दोबारा प्रयास करें।", reply_markup=ReplyKeyboardRemove())
        print("Error:", e)

# फोटो हैंडलर
@bot.message_handler(content_types=['photo'])
def handle_photo_message(message):
    user_id = message.chat.id
    user_data = None
    
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?user_id=eq.{user_id}&select=name,goal,diet",
            headers=SUPABASE_HEADERS
        )
        if response.status_code == 200 and response.json():
            user_data = response.json()[0]
    except Exception as e:
        print("Supabase fetch error in photo:", e)
        
    if user_data:
        name = user_data.get('name')
        goal = user_data.get('goal')
        diet = user_data.get('diet')
        caption = message.caption if message.caption else ""
        
        bot.send_chat_action(message.chat.id, 'typing')
        
        if caption:
            loading_msg = f"📸 {name}, फोटो और नोट ('{caption}') मिल गए हैं! AI कैलोरी स्कैन कर रहा है... ⏳"
        else:
            loading_msg = f"📸 {name}, फोटो मिल गई है! AI कैलोरी स्कैन कर रहा है... ⏳"
            
        bot.send_message(message.chat.id, loading_msg)
        
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            analysis_result = analyze_meal_photo(downloaded_file, caption, name, goal, diet)
            send_long_message(message.chat.id, analysis_result)
        except Exception as e:
            print("Photo processing error:", e)
            bot.send_message(message.chat.id, "⚠️ फोटो प्रोसेस करने में दिक्कत आई।")
    else:
            bot.send_message(message.chat.id, "⚠️ पहले कृपया 'Create Profile 📝' बटन पर क्लिक करके अपनी प्रोफाइल बनाएं!")

# स्मार्ट टेक्स्ट Q&A चैट हैंडलर
@bot.message_handler(func=lambda message: True)
def handle_all_text_messages(message):
    user_id = message.chat.id
    user_query = message.text
    user_data = None
    
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?user_id=eq.{user_id}&select=name,age,gender,height,weight,goal,diet",
            headers=SUPABASE_HEADERS
        )
        if response.status_code == 200 and response.json():
            user_data = response.json()[0]
    except Exception as e:
        print("Supabase fetch error in text:", e)
        
    if user_data:
        name = user_data.get('name')
        age = user_data.get('age')
        gender = user_data.get('gender')
        height = user_data.get('height')
        weight = user_data.get('weight')
        goal = user_data.get('goal')
        diet = user_data.get('diet')
        
        bot.send_chat_action(message.chat.id, 'typing')
        reply_text = generate_ai_text_reply(name, age, gender, height, weight, goal, diet, user_query)
        send_long_message(message.chat.id, reply_text)
    else:
        bot.send_message(message.chat.id, "⚠️ कृपया पहले 'Create Profile 📝' बटन पर क्लिक करके अपनी प्रोफाइल बनाएं!")

# --- MAIN ENTRY POINT ---
if __name__ == '__main__':
    print("Starting Telegram Bot on Render with Supabase Database...")
    bot_thread = threading.Thread(target=run_flask)
    bot_thread.daemon = True
    bot_thread.start()

    while True:
        try:
            print("Bot polling started...")
            # सुरक्षित वेबहुक रिमूव कॉल (बिना skip_pending के)
            bot.remove_webhook()
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Connection lost ({e}). Retrying in 5 seconds...")
            time.sleep(5)

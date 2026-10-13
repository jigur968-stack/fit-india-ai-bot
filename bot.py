import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, WebAppInfo
import json
import os
import time
import requests
from google import genai
from PIL import Image
from io import BytesIO
from flask import Flask
import threading

# --- RENDER WEB SERVER SETUP (रेंडर हेल्थ चेक के लिए) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Fit India AI Bot is running smoothly with Multi-AI Cascade Engine on Render! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
# --------------------------------------------------------

# Environment Variables से Tokens और Supabase Credentials उठाना (.strip() सुरक्षा के लिए)
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

if not BOT_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: आवश्यक टोकन या Supabase Credentials नहीं मिले! कृपया Render Environment Variables चेक करें।")
    exit()

# Supabase REST API Headers
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Google GenAI Modern Client Setup
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

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

# ⚡ ULTIMATE MULTI-AI CASCADE ROUTER (Groq -> Gemini Flash -> Gemini Pro -> OpenAI)
def call_multi_ai(prompt, image=None):
    gemini_models = ['gemini-3.8-flash', 'gemini-3.1-pro-preview']

    # 1. फोटो स्कैन (Vision) के लिए Gemini मॉडल्स की क्रमिक श्रृंखला
    if image:
        if gemini_client:
            for m in gemini_models:
                try:
                    res = gemini_client.models.generate_content(
                        model=m,
                        contents=[prompt, image]
                    )
                    if res and res.text:
                        return res.text
                except Exception as e:
                    print(f"Gemini Vision ({m}) Error: {e}")
                    time.sleep(1)
        return "⚠️ फोटो स्कैन करने में समस्या आई। कृपया पुनः प्रयास करें!"

    # 2. टेक्स्ट चैट के लिए: Step A - Groq Llama 3.3 (सुपर-फास्ट प्राइमरी: 1-2 सेकंड)
    if GROQ_API_KEY:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                return res.json()['choices'][0]['message']['content']
            else:
                print(f"Groq Failed ({res.status_code}): {res.text}")
        except Exception as e:
            print(f"Groq Exception: {e}")

    # 3. टेक्स्ट चैट के लिए: Step B - Gemini Models Backup (3.8-flash & 3.1-pro-preview)
    if gemini_client:
        for m in gemini_models:
            try:
                res = gemini_client.models.generate_content(
                    model=m,
                    contents=prompt
                )
                if res and res.text:
                    return res.text
            except Exception as e:
                print(f"Gemini Model ({m}) Fallback Error: {e}")
                time.sleep(1)

    # 4. टेक्स्ट चैट के लिए: Step C - OpenAI Backup (अंतिम सुरक्षा चक्र)
    if OPENAI_API_KEY:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}]
            }
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                return res.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"OpenAI Fallback Error: {e}")

    return "⚠️ सभी AI सर्विसेज अभी व्यस्त हैं। कृपया 5 सेकंड बाद पुनः प्रयास करें!"

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
    return call_multi_ai(prompt)

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
    return call_multi_ai(prompt, image)

# AI टेक्स्ट चैट Q&A का फंक्शन
def generate_ai_text_reply(name, age, gender, height, weight, goal, diet, user_query):
    prompt = f"""
    आप Fit India AI के स्मार्ट फिटनेस कोच हैं।
    प्रोफाइल: {name}, {age}वर्ष, {gender}, Goal: {goal}, Diet: {diet}.
    सवाल: "{user_query}"

    संक्षिप्त, सटीक और मददगार जवाब हिंदी (Hinglish mix) में दें।
    """
    return call_multi_ai(prompt)

# स्टार्ट कमांड
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    user_data = None
    
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?user_id=eq.{user_id}&select=name,goal,diet",
            headers=SUPABASE_HEADERS
        )
        if response.status_code == 200:
            data = response.json()
            if data:
                user_data = data[0]
    except Exception as e:
        print("Supabase fetch error in start:", e)
    
    if not user_data or not user_data.get('name'):
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("Create Profile 📝", web_app=WebAppInfo(url=WEBAPP_URL)))
        text_message = "Fit India AI में आपका स्वागत है! 🇮🇳\n\nकृपया अपनी फिटनेस प्रोफाइल बनाने के लिए नीचे दिए गए 'Create Profile 📝' बटन पर क्लिक करें:"
        bot.send_message(message.chat.id, text_message, reply_markup=markup)
    else:
        name = user_data.get('name')
        goal = user_data.get('goal', 'Fitness')
        diet = user_data.get('diet', 'Veg')
        
        text_message = (
            f"नमस्ते {name}! Fit India AI में आपका स्वागत है। 🇮🇳\n\n"
            f"मैं आपका पर्सनल AI फिटनेस कोच हूँ। आपकी प्रोफाइल (**{goal} | {diet}**) के अनुसार आप मेरा इस्तेमाल इन तरीकों से कर सकते हैं:\n\n"
            f"1. 🏋️‍♂️ **वर्कआउट गाइड:** मुझसे अपनी पसंद का होम या जिम वर्कआउट रूटीन बनवा सकते हैं।\n"
            f"2. 🥗 **डाइट और मील प्लान:** अपने लक्ष्य ({goal}) और डाइट ({diet}) के हिसाब से डाइट चार्ट मांग सकते हैं।\n"
            f"3. 📸 **फोटो से कैलोरी स्कैन:** अपने खाने की फोटो भेजकर उसमें मौजूद कैलोरी और मैक्रोज़ जान सकते हैं।\n"
            f"4. 💡 **फिटनेस सलाह:** सप्लीमेंट, न्यूट्रिशन, या वर्कआउट से जुड़ा कोई भी सवाल सीधे पूछ सकते हैं।\n\n"
            f"👇 *आपको जो भी मदद चाहिए, बस नीचे सीधे टाइप करें!*"
        )
        bot.send_message(message.chat.id, text_message, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")

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
            bot.send_message(message.chat.id, f"⚠️ Supabase Error: {res.text}", reply_markup=ReplyKeyboardRemove())
        
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ WebApp Processing Error: {e}", reply_markup=ReplyKeyboardRemove())
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
            bot.send_message(message.chat.id, f"⚠️ Photo Handler Error: {e}")
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
        bot.send_message(message.chat.id, "⚠️ पहले कृपया 'Create Profile 📝' बटन पर क्लिक करके अपनी प्रोफाइल बनाएं!")

# --- MAIN ENTRY POINT ---
if __name__ == '__main__':
    print("Starting Telegram Bot on Render with Ultimate Multi-AI Cascade Engine...")
    bot_thread = threading.Thread(target=run_flask)
    bot_thread.daemon = True
    bot_thread.start()

    # पुराने अटके हुए वेबहुक / मैसेज साफ़ करना
    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception as e:
        print("Webhook Removal Warning:", e)

    while True:
        try:
            print("Bot polling started...")
            bot.infinity_polling(timeout=20, long_polling_timeout=20, skip_pending=True)
        except Exception as e:
            print(f"Connection lost ({e}). Retrying in 5 seconds...")
            time.sleep(5)

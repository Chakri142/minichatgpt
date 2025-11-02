import datetime
import requests
import wikipediaapi
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from transformers import AutoModelForCausalLM, AutoTokenizer

# --- Initialize Flask App ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key_you_should_change' 

# --- Database & Session Configuration ---
DB_NAME = 'chat.db'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY_TABLE'] = 'sessions'

db = SQLAlchemy(app) # Create our DB instance

# Tell Flask-Session to use our 'db' instance
app.config['SESSION_SQLALCHEMY'] = db 

sess = Session(app) # Now initialize Session
CORS(app, supports_credentials=True) 

# Define our 'conversation' table as a SQLAlchemy Model
class Conversation(db.Model):
    id = db.Column(db.String(255), primary_key=True) # This will be the session ID
    history_text = db.Column(db.Text)

# Create all tables (both 'sessions' and 'conversation')
with app.app_context():
    db.create_all()

# --- Load Model ---
print("Loading MEDIUM model...")
tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium")
model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-medium")
print("Model loaded!")

# --- Initialize Tools ---
wiki_wiki = wikipediaapi.Wikipedia('MyChatbot (merlin@example.com)', 'en')
MAX_CONTEXT_TOKENS = 800 

@app.route('/get_history', methods=['GET'])
def get_history():
    session.permanent = True
    session_id = session.sid
    
    # Use SQLAlchemy to get history
    conversation = Conversation.query.get(session_id)
    
    if conversation:
        # User has an existing history
        history = conversation.history_text
    else:
        # This is a new user. Create a default history for them.
        history = "Bot: Hello! I'm your AI assistant. How can I help?\n"
        new_convo = Conversation(id=session_id, history_text=history)
        db.session.add(new_convo)
        db.session.commit()
        
    return jsonify({'history': history})


@app.route('/chat', methods=['POST'])
def chat():
    try:
        session_id = session.sid # Get the user's ID
        
        # --- Get data from the request ---
        data = request.json
        user_message = data['message']
        history_string = data.get('history', '')
        normalized_message = user_message.lower().strip()

        # --- Tool Logic ---
        reply = None
        if "what is the time" in normalized_message:
            now = datetime.datetime.now()
            reply = f"The current time is {now.strftime('%I:%M %p')}."
            
        elif "what is the date" in normalized_message:
            now = datetime.datetime.now()
            reply = f"Today's date is {now.strftime('%A, %B %d, %Y')}."
            
        elif "weather in" in normalized_message:
            try:
                city = user_message.split("weather in")[-1].strip().replace("?", "")
                geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
                geo_res = requests.get(geo_url)
                geo_data = geo_res.json()
                lat = geo_data['results'][0]['latitude']
                lon = geo_data['results'][0]['longitude']
                weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                weather_res = requests.get(weather_url)
                weather_data = weather_res.json()
                temp = weather_data['current_weather']['temperature']
                wind = weather_data['current_weather']['windspeed']
                reply = f"The current weather in {city.title()} is {temp}°C with wind speeds of {wind} km/h."
            except Exception as e:
                print(f"Weather tool error: {e}")
                reply = "Sorry, I couldn't find that city's weather."
                
        elif normalized_message.startswith(("what is ", "what's ", "who is ", "who's ")):
            try:
                query = user_message.split(" ", 2)[-1].replace("?", "")
                page = wiki_wiki.page(query)
                reply = page.summary.split('\n')[0] if page.exists() else f"Sorry, I couldn't find any Wikipedia information on '{query}'."
            except Exception as e:
                print(f"Wikipedia tool error: {e}")
                reply = "Sorry, I had trouble looking that up on Wikipedia."

        # --- AI Model Logic ---
        if reply is None:
            user_prompt = "User: " + user_message + "\nBot:"
            full_prompt_string = history_string + user_prompt
            input_ids = tokenizer.encode(full_prompt_string, return_tensors='pt')
            if input_ids.shape[-1] > MAX_CONTEXT_TOKENS:
                input_ids = input_ids[:, -MAX_CONTEXT_TOKENS:]
                full_prompt_string = tokenizer.decode(input_ids[0], skip_special_tokens=True)
                if not full_prompt_string.endswith("\nBot:"):
                     full_prompt_string += "\nBot:"
            output_ids = model.generate(
                input_ids, max_new_tokens=60, pad_token_id=tokenizer.eos_token_id,
                do_sample=True, top_k=50, top_p=0.95, temperature=0.7, no_repeat_ngram_size=3
            )
            reply = tokenizer.decode(output_ids[:, input_ids.shape[-1]:][0], skip_special_tokens=True)

        # --- Save to DB and Send Response ---
        new_history = history_string + "User: " + user_message + "\nBot: " + reply + "\n"
        
        try:
            # Use SQLAlchemy to save history
            conversation = Conversation.query.get(session_id)
            conversation.history_text = new_history
            db.session.commit()
        except Exception as e:
            print(f"Error saving to DB: {e}")

        return jsonify({'reply': reply, 'new_history': new_history})

    except Exception as e:
        print(f"Error in /chat: {e}")
        return jsonify({"error": str(e)}), 500
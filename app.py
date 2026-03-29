import torch
import gc # Garbage collector to free RAM
import re
import ast
import joblib
import textstat
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from collections import Counter

# INSTALL BELOW IN TERMINAL THE RUN app.py
#pip install flask flask-cors transformers torch textstat joblib pandas  
app = Flask(__name__)
CORS(app) 

# AUTO-SPEED: Automatically use your computer's GPU if available
device = "cuda" if torch.cuda.is_available() else "cpu"

# --- 1. LOAD THE DIFFICULTY MODEL (Random Forest) ---
try:
    # This loads the model you trained in Jupyter
    rf_model = joblib.load("difficulty_rf_model.pkl")
    print("--- Random Forest Difficulty Classifier Loaded! ---")
except Exception as e:
    print(f"--- Warning: Could not load difficulty_rf_model.pkl: {e} ---")
    rf_model = None

# Global variables for Transformers
current_model = None
current_tokenizer = None
current_task_type = None 

PATH_MAIN = "prem415/my-chrome-summarizer"  
PATH_MCQ = "Minnu21/my-chrome-mcqmodel" 

# --- DIFFICULTY PREDICTION HELPERS ---
def extract_features(text):
    """Extracts linguistic features for the Random Forest model."""
    return {
        'flesch_reading_ease': textstat.flesch_reading_ease(text),
        'smog_index': textstat.smog_index(text),
        'avg_sentence_length': len(text.split()) / max(1, len(text.split('.'))),
        'avg_word_length': sum(len(word) for word in text.split()) / max(1, len(text.split())),
        'difficult_words': textstat.difficult_words(text)
    }

def predict_difficulty(text):
    """Predicts if a sentence is Easy, Medium, or Hard."""
    if rf_model is None:
        return "Medium"
    try:
        features = extract_features(text)
        df_feat = pd.DataFrame([features])
        prediction = rf_model.predict(df_feat)[0]
        mapping = {0: "Easy", 1: "Medium", 2: "Hard"}
        return mapping.get(prediction, "Medium")
    except:
        return "Medium"

def load_model(task_type):
    global current_model, current_tokenizer, current_task_type
    if current_task_type == task_type:
        return
    print(f"--- Swapping model to: {task_type.upper()} ---")
    if current_model is not None:
        del current_model
        del current_tokenizer
        gc.collect() 
        if device == "cuda":
            torch.cuda.empty_cache()

    path = PATH_MCQ if task_type == "mcq" else PATH_MAIN
    print(f"Loading '{path}'...")
    current_tokenizer = AutoTokenizer.from_pretrained(path)
    current_model = AutoModelForSeq2SeqLM.from_pretrained(path).to(device)
    current_task_type = task_type
    print(f"--- {task_type.upper()} model loaded successfully on {device.upper()}! ---")


def clean_and_validate_mcq(mcq_text, distractors_pool=[]):
    try:
        question = ""
        options = []
        answer = ""

        if "question:" in mcq_text.lower():
            question = mcq_text.split("question:", 1)[1].split("options:")[0].strip()
            
        if not question.endswith("?") or len(question) < 15:
            return None
            
        bad_phrases = ["multiple choice", "how many option", "correct answer", "generate a"]
        for bad in bad_phrases:
            if bad in question.lower(): return None

        if "options:" in mcq_text.lower():
            opt_part = mcq_text.split("options:", 1)[1].split("answer:")[0].strip()
            try:
                options = ast.literal_eval(opt_part)
            except:
                options = re.findall(r"'(.*?)'", opt_part)

        if "answer:" in mcq_text.lower():
            answer = mcq_text.split("answer:", 1)[1].strip().strip('.,;:"!?()[]')

        if not answer: return None

        # Logic for cleaning and deduplication
        import difflib
        clean_options = [opt.strip('.,;:"!?()[]') for opt in options if len(opt.strip()) > 1]
        
        final_clean_options = [answer]
        for opt in clean_options:
            if not any(difflib.SequenceMatcher(None, opt.lower(), f.lower()).ratio() > 0.85 for f in final_clean_options):
                final_clean_options.append(opt)
        
        # Add distractors if needed
        if len(final_clean_options) < 4 and distractors_pool:
            import random
            random.shuffle(distractors_pool)
            for d in distractors_pool:
                if not any(difflib.SequenceMatcher(None, d.lower(), f.lower()).ratio() > 0.85 for f in final_clean_options):
                    final_clean_options.append(d)
                if len(final_clean_options) == 4: break

        while len(final_clean_options) < 4:
            fillers = ["None of the above", "All of the above", "Both A and B"]
            for f in fillers:
                if f not in final_clean_options: final_clean_options.append(f)
                if len(final_clean_options) == 4: break

        final_clean_options = final_clean_options[:4]
        import random
        random.shuffle(final_clean_options)

        return {
            "question": question,
            "options": final_clean_options,
            "answer": answer
        }
    except:
        return None

@app.route('/process', methods=['POST'])
def process_text():
    data = request.json
    text = data.get("text", "")
    task = data.get("task", "summarize")

    if not text:
        return jsonify({"error": "No text found"}), 400

    try:
        safe_text = text[:12000] 

        if task in ["mcq", "flashcards"]:
            load_model("mcq")
            
            # --- Distractor Extraction ---
            distractors_pool = []
            try:
                cap_phrases = re.findall(r'\b[A-Z][a-z]+(?: [A-Z][a-z]+)+\b', safe_text)
                words = re.findall(r'\b[a-zA-Z]{5,15}\b', safe_text.lower())
                common_words = [w.capitalize() for w, c in Counter(words).most_common(50)]
                distractors_pool = list(set(cap_phrases + common_words))
            except: pass
            
            sentences = re.split(r'[.!?]', safe_text)
            # REMOVED [:25] HERE - Gives the model unlimited attempts to find 10 good ones
            sentences = [s.strip() for s in sentences if len(s.split()) > 8] 
            
            valid_items = []
            for sentence in sentences:
                # 1. PREDICT DIFFICULTY FOR THIS SPECIFIC SENTENCE
                difficulty_label = predict_difficulty(sentence)

                # 2. GENERATE QUESTION
                input_text = "Generate a multiple choice question with 4 meaningful options and one correct answer: " + sentence
                inputs = current_tokenizer.encode(input_text, return_tensors="pt", truncation=True, max_length=512).to(device)

                with torch.no_grad():
                    outputs = current_model.generate(inputs, max_length=256, num_beams=4, early_stopping=True)
                
                result = current_tokenizer.decode(outputs[0], skip_special_tokens=True)
                cleaned = clean_and_validate_mcq(result, distractors_pool)
                
                if cleaned:
                    if not any(mq['question'] == cleaned['question'] for mq in valid_items):
                        # 3. ATTACH DIFFICULTY TO THE ITEM
                        cleaned['difficulty'] = difficulty_label
                        valid_items.append(cleaned)
                
                # BREAKS THE LOOP THE EXACT SECOND WE HIT 10
                if len(valid_items) >= 10: 
                    break

            return jsonify({"items": valid_items, "task": task})
                
        else:
            # Main model tasks (summarize)
            load_model("main") 
            input_text = "summarize: " + safe_text
            input_ids = current_tokenizer(input_text, return_tensors="pt", max_length=1500, truncation=True).input_ids.to(device)
            
            with torch.no_grad():
                outputs = current_model.generate(input_ids, max_length=450, min_length=100, num_beams=4, length_penalty=2.0,   # Encourages longer output
                    early_stopping=True)
                
            result = current_tokenizer.decode(outputs[0], skip_special_tokens=True)
            return jsonify({"result": result, "task": task})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Initializing Server...")
    load_model("main")
    app.run(debug=True, port=5000)
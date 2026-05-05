# AI Student Companion 🎓

An intelligent Chrome extension that transforms passive web reading into an active learning experience. This tool extracts raw web content and uses advanced NLP models to instantly generate structured summaries, Multiple Choice Questions (MCQs), and flashcards directly in your browser.

## 🚀 Features

*   **Abstractive Summarization:** Condenses long articles into concise, highly readable summaries using Flan-T5, achieving up to 90% data compression while maintaining context.
*   **Auto-Quiz Generation:** Automatically generates MCQs with contextually relevant, AI-generated distractors to test reading comprehension on the fly.
*   **Instant Flashcards:** Identifies key definitions and concepts, formatting them into front/back study cards.
*   **Distraction-Free Extraction:** Bypasses ads, navbars, and boilerplate HTML to focus solely on the core educational text.
*   **Real-time Processing:** Low-latency inference (2-4 seconds) delivered via a seamless popup interface.

## 🏗️ System Architecture

The project relies on a decoupled frontend-backend architecture:
1.  **Frontend (Chrome Extension):** Built with HTML/CSS/JS. Handles user triggers, captures the current active tab, and renders the generated study materials in a tabbed UI.
2.  **Backend (Flask API):** Processes the raw text. Utilizes a sliding-window chunking mechanism (512 tokens) to handle large articles.
3.  **NLP Engine:** 
    *   *Summarization:* Fine-tuned HuggingFace Flan-T5 model.
    *   *MCQs:* T5-based pipeline combined with spaCy for sentence segmentation and semantic embeddings for distractor generation.
    *   *Classification:* Random Forest & SVM models utilizing BERT embeddings to evaluate sentence complexity and relevance.

## 🛠️ Tech Stack

*   **Frontend:** HTML5, CSS3, JavaScript, Chrome Extensions API (Manifest V3)
*   **Backend:** Python 3.x, Flask
*   **Machine Learning / NLP:** HuggingFace Transformers (T5/Flan-T5), spaCy, NLTK, Scikit-Learn
*   **Data Scraping:** BeautifulSoup4

## ⚙️ Installation & Setup

### Prerequisites
*   Python 3.8+
*   Google Chrome browser

### 1. Backend Setup
1. Clone the repository:
   ```bash
   git clone [https://github.com/Duocross415/Ai-chrome-extension-assistant.git](https://github.com/Duocross415/Ai-chrome-extension-assistant.git)
   cd Ai-chrome-extension-assistant/backend
   Install the required Python dependencies:

Bash
pip install -r requirements.txt
Download the necessary NLP models (spaCy english core, etc.):

Bash
python -m spacy download en_core_web_sm
Start the Flask server:

Bash
python app.py

   *The server should now be running on `http://localhost:5000`.*

### 2. Chrome Extension Setup
1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Toggle **Developer mode** on (top right corner).
3. Click **Load unpacked** and select the `frontend/extension` folder from this repository.
4. The AI Student Companion icon will now appear in your browser toolbar.

## 💡 Usage

1. Navigate to any text-heavy educational article or blog post.
2. Click the **AI Student Companion** extension icon in your toolbar.
3. Click **"Analyze Page"**.
4. Browse through the generated Summaries, Quizzes, and Flashcards using the extension's tabbed interface.

## 🔮 Future Enhancements

*   **LMS Integration:** Export capabilities to Anki, Notion, and Google Classroom.
*   **Persistent Storage:** Implementation of a relational database (e.g., MySQL) to track user progress, save flashcard decks, and build an ongoing study portfolio.
*   **Multilingual Support:** Translation modules to process and learn from non-English content.
*   **Audio Mode:** Text-to-speech features for on-the-go auditory learning.

// Function to scrape main content from the 

function scrapeWebpageText() {
    let clone = document.body.cloneNode(true);
    const junkTags = ['nav', 'aside', 'footer', 'header', 'script', 'style', 'noscript', 'iframe', 'svg', 'form', 'button'];
    junkTags.forEach(tag => {
        let elements = clone.querySelectorAll(tag);
        elements.forEach(el => el.remove());
    });
    
    let mainContent = clone.querySelector('article') || clone.querySelector('main') || document.body;
    let goodElements = mainContent.querySelectorAll('p, h1, h2, h3, h4, li');
    let fullText = Array.from(goodElements)
        .map(el => el.innerText.trim())
        .filter(text => text.length > 30)
        .join('\n\n');
    return fullText;
}

async function processWithAI(taskName) {
    const resultDiv = document.getElementById('result');
    const loader = document.getElementById('loader');
    const quizContainer = document.getElementById('quiz-container');
    const flashcardContainer = document.getElementById('flashcard-container');

    // Reset UI
    resultDiv.innerText = "";
    loader.style.display = "block";
    quizContainer.style.display = "none";
    flashcardContainer.style.display = "none";
    resultDiv.style.display = (taskName === 'summarize') ? "block" : "none";

    try {
        let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        let injectionResults = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: scrapeWebpageText,
        });

        let pageText = injectionResults[0].result;
        if (!pageText || pageText.length < 50) {
            loader.style.display = "none";
            resultDiv.style.display = "block";
            resultDiv.innerText = "Error: Website content too short.";
            return;
        }

        const response = await fetch('http://localhost:5000/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: pageText, task: taskName })
        });

        const data = await response.json();
        loader.style.display = "none";

        if (data.items && data.items.length > 0) {
            if (taskName === 'mcq') {
                quizContainer.style.display = "flex";
                quizContainer.innerHTML = "";
                data.items.forEach((mcq, index) => {
                    const block = document.createElement('div');
                    block.className = 'mcq-block';

                    // --- NEW: DIFFICULTY TAG ---
                    if (mcq.difficulty) {
                        const dTag = document.createElement('span');
                        dTag.className = `mcq-difficulty-tag diff-${mcq.difficulty.toLowerCase()}`;
                        dTag.innerText = mcq.difficulty;
                        block.appendChild(dTag);
                    }

                    const question = document.createElement('p');
                    question.className = 'mcq-question';
                    question.innerText = `${index + 1}. ${mcq.question}`;
                    block.appendChild(question);

                    const feedback = document.createElement('span');
                    feedback.className = 'mcq-feedback';
                    const optionsContainer = document.createElement('div');
                    const optionButtons = [];

                    mcq.options.forEach((opt) => {
                        const btn = document.createElement('button');
                        btn.className = 'mcq-option';
                        btn.innerText = opt;
                        btn.addEventListener('click', () => {
                            optionButtons.forEach(b => b.disabled = true);
                            if (opt === mcq.answer) {
                                btn.classList.add('correct');
                                feedback.innerText = "✔ Correct!";
                                feedback.className = "mcq-feedback correct";
                            } else {
                                btn.classList.add('wrong');
                                feedback.innerText = "✘ Incorrect";
                                feedback.className = "mcq-feedback wrong";
                                const correctBtn = optionButtons.find(b => b.innerText === mcq.answer);
                                if (correctBtn) correctBtn.classList.add('correct');
                            }
                        });
                        optionButtons.push(btn);
                        optionsContainer.appendChild(btn);
                    });
                    block.appendChild(optionsContainer);
                    block.appendChild(feedback);
                    quizContainer.appendChild(block);
                });
            } else if (taskName === 'flashcards') {
                flashcardContainer.style.display = "flex";
                flashcardContainer.innerHTML = "";
                data.items.forEach(item => {
                    const card = document.createElement('div');
                    card.className = 'flashcard';
                    card.innerHTML = `
                        <div class="flashcard-inner">
                            <div class="flashcard-front">${item.question}<div class="flashcard-hint">Tap for Answer</div></div>
                            <div class="flashcard-back">${item.answer}<div class="flashcard-hint">Tap for Question</div></div>
                        </div>`;
                    card.addEventListener('click', () => card.classList.toggle('flipped'));
                    flashcardContainer.appendChild(card);
                });
            }
        } else if (data.result) {
            resultDiv.style.display = "block";
            resultDiv.innerHTML = `<h3>Summary</h3><p>${data.result}</p>`;
        }
    } catch (error) {
        loader.style.display = "none";
        resultDiv.style.display = "block";
        resultDiv.innerText = "Connection Failed! Is app.py running?";
    }
}

document.addEventListener('DOMContentLoaded', () => {
    let currentTask = "summarize";
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentTask = e.target.getAttribute('data-task');
            document.getElementById('btn-generate').innerText = `Generate ${currentTask.charAt(0).toUpperCase() + currentTask.slice(1)}`;
            
            // Clear current view
            document.getElementById('result').innerText = "Click generate to scan.";
            document.getElementById('quiz-container').style.display = "none";
            document.getElementById('flashcard-container').style.display = "none";
        });
    });

    document.getElementById('btn-generate').addEventListener('click', () => processWithAI(currentTask));
    document.getElementById('btn-close').addEventListener('click', () => window.close());
});
const closeBtn = document.getElementById('btn-close');
if (closeBtn) {
    closeBtn.addEventListener('click', () => {
        // This sends a message to content.js to hide the iframe
        window.parent.postMessage({ action: "closeAIWidget" }, "*");
    });
}
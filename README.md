# HHAssist

## 🚀 Project Description

HHAssist is an automated assistant for working with the HeadHunter
(hh.ru) job platform. It helps simplify routine tasks: analyzing a job
posting, writing a personalized cover letter, and answering questions
based on your resume and the vacancy you are considering.

Users can not only compare their skills with job requirements but also
ask questions to improve their resume.

Use the bot on Telegram: https://t.me/hhassistentBot

------------------------------------------------------------------------

## ✨ Key Features

-   🤖 Automatic cover letter generation
-   📊 Resume strengths & weaknesses analysis
-   🤓 Answers to questions based on your resume and the selected vacancy
-   🐳 Full Dockerization
-   🧠 LLM integration

------------------------------------------------------------------------

## 🏗️ Project Architecture

    HHAssist/
    │
    ├─ app/
    │   ├─ bot.py
    │   ├─ analyzer.py
    │   └─ parser.py
    ├─ Dockerfile
    ├─ Dockerfile.ollama
    ├─ docker-compose.yml
    ├─ requirements.txt
    └─ README.md

------------------------------------------------------------------------

## ⚙️ Installation & Setup

### 📦 With Docker

1.  Create and configure the `.env` file in the project root:
   
```
TELEGRAM_BOT_TOKEN="YOUR_TG_BOT_API_KEY"
REDIS_URL=redis://hhassist-redis:6379/0
OLLAMA_MODEL=gpt-oss:120b-cloud
OLLAMA_BASE_URL=http://hhassist-ollama:11434
```

2.  Start Docker:

``` bash
git clone https://github.com/NickS0kolov/HHAssist.git
cd HHAssist
docker compose build
docker compose up -d
```

3.  Authenticate in Ollama:

``` bash
docker exec -it hhassist-ollama bash
ollama run gpt-oss:120b-cloud
ollama singin
```

------------------------------------------------------------------------

## 📝 Usage

1.  Send your resume in PDF/DOC format (stored in memory for 48 hours).
2.  Send a link to a vacancy from HeadHunter.
3.  Receive the response.
4.  Ask optional questions - the model will answer based on the
    current vacancy and your resume.

------------------------------------------------------------------------

## 🤝 Contributing

Contributions are welcome!

    1. Fork → 2. Create a new branch → 3. Commit → 4. Pull Request

------------------------------------------------------------------------

## 📄 License

This project is distributed under the **MIT License**.

------------------------------------------------------------------------

## 📬 Contact

Author: Nick Sokolov\
GitHub: https://github.com/NickS0kolov

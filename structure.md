# PROJECT STRUCTURE

hr-ai-assistant/

app/

* main.py
* routes.py
* ui.py

core/

* rag_pipeline.py
* embeddings.py
* retriever.py   # Supabase
* llm.py         # Gemini
* guardrails.py

evaluation/

* eval_runner.py
* grading.py
* groundedness.py
* test_cases.json

data/

* raw/hr_docs/
* processed/

prompts/

* system_prompt.txt
* guardrail_prompt.txt
* grading_prompt.txt
* groundedness_prompt.txt

scripts/

* ingest_data.py
* build_index.py

config/

* settings.yaml

README.md
requirements.txt

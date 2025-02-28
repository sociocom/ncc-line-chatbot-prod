run:
	rye run uvicorn src.rule:app --reload --port=3300

run-d:
	rye run uvicorn src.rule:app --reload --host=0.0.0.0 --host=3300

connect:
	ngrok http 8000 --region jp

docker-run:
	docker run -it --rm -p 3300:3300 \
	--name ncc-line-chatbot-prod \
	-v $(PWD)/data:/bot/data \
	-v $(PWD)/src:/bot/src \
	ncc-line-chatbot-prod \
	/bin/bash -c "source ~/.bashrc && rye run uvicorn src.rule:app --reload --host=0.0.0.0 --port=3300"

docker-run-d:
	docker run -d --rm -p 3300:3300 \
	--name ncc-line-chatbot-prod \
	-v $(PWD)/data:/bot/data \
	-v $(PWD)/src:/bot/src \
	ncc-line-chatbot-prod \
	/bin/bash -c "source ~/.bashrc && rye run uvicorn src.rule:app --reload --host=0.0.0.0 --port=3300"

build:
	docker build . -t ncc-line-chatbot-prod
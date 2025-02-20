run:
	rye run uvicorn src.rule:app --reload --port=3000

run-d:
	rye run uvicorn src.rule:app --reload --host=0.0.0.0 --host=3000

connect:
	ngrok http 8000 --region jp

docker-run:
	docker run -it --rm -p 3000:3000 \
	--name ncc-line-chatbot-prod \
	-v $(PWD)/data:/bot/data \
	-v $(PWD)/src:/bot/src \
	ncc-line-chatbot-poc \
	/bin/bash -c "source ~/.bashrc && rye run uvicorn src.rule:app --reload --host=0.0.0.0 --port=3000"

docker-run-d:
	docker run -d --rm -p 3000:3000 \
	--name ncc-line-chatbot-prod \
	-v $(PWD)/data:/bot/data \
	-v $(PWD)/src:/bot/src \
	ncc-line-chatbot-poc \
	/bin/bash -c "source ~/.bashrc && rye run uvicorn src.rule:app --reload --host=0.0.0.0 --port=3000"

build:
	docker build . -t ncc-line-chatbot-prod
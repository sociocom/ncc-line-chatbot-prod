import pandas as pd
import numpy as np

from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


class FaqService:
    def __init__(self, faq_data_path):
        self.data = pd.read_csv(faq_data_path)
        self.questions = self.data["Question"].fillna("")
        self.answers = self.data["Answer"].fillna("")
        self.url = self.data["URL"].fillna("")
        self.qestion_interpreting = self.data["Qestion_interpreting"].fillna("")
        self.option = self.data["Option"].fillna("")
        self.option_question = self.data["Option_question"].fillna("")
        self.model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.model.eval()
        self.embeddings = self.model.encode(self.questions.values)

    def find_similar(self, input_text):
        input_embedding = self.model.encode([input_text])
        similarity_scores = cosine_similarity(input_embedding, self.embeddings)
        most_similar_index = np.argmax(similarity_scores)
        return most_similar_index

    def get_response(self, input_text):
        similar_question_index = self.find_similar(input_text)
        response_url = self.url[similar_question_index]
        response = [self.answers[similar_question_index]]
        option = self.option[similar_question_index]
        option_question = self.option_question[similar_question_index]
        if response_url != "":
            urls = response_url.split("\t")
            response.extend(list(urls))
        else:
            if option != "":
                option = option.split("\t")
                option_question = option_question.split("\t")
                response = [self.qestion_interpreting[similar_question_index]]
            else:
                print("option: None")

        return response, option, option_question, similar_question_index


# データセットのパス
faq_data_path = "./data/inputs/NCC_FAQdata_20250115_for_line.csv"

# FaqServiceの初期化
faq_service = FaqService(faq_data_path)


def find_answer(input_text) -> str:
    # 応答の取得
    response, option, option_question = faq_service.get_response(input_text)

    return response


def find_option(input_text) -> str:
    # 応答の取得
    response, option, option_question, index = faq_service.get_response(input_text)

    return response, option, option_question, index

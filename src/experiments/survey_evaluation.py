import random
import json
import re
from collections import defaultdict, Counter
from typing import Dict, Optional, List

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# This file was created with the help of ChatGPT

# Path to the service account key file
SERVICE_ACCOUNT_FILE = "bachelor-thesis-448517-457f4122d888.json"

# Scopes required for the Google Forms API
SCOPES = [
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/forms.body.readonly",
]

# Authenticate using the service account
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build("forms", "v1", credentials=credentials)

_ids = [
    "1D9Y6rpGKC_3ly9csjrBA4cADcBEmXHDXtfDLNKF93TM",
    "1nw4f9f_Zo4TC85AORuXjD_UdYrY5fZXpwMImUWms3LM",
    "1nnI7X-42hjRSma48R_idPmF7GqKaYYGfJvJZJ3iBg0M",
    "1OoTZY-WYRG_3sOwqoSj4XeodC70n2DKm5R875YvqEPI",
    "1K53PFsWs4gIOAQ_bxosQ3KvEomLBD3ytUTGDm0X-e9E",
    "1QCdcKBLtkZnt30AZ28LEv1uoKXyRGKkosGlxiqITmJI",
    "1RVTodXgaKK4hyAdQQS1t8eNRsfzovIUx7_wL58ZsAWs",
    "1jB4YFnFqZSRH8qcnhTR5CCZQS49hdJJqnkhfWqBVzjE",
]


def get_form_responses(form_id: str) -> Optional[List[Dict[str, str]]]:
    try:
        _response = service.forms().responses().list(formId=form_id).execute()
        _responses = _response.get("responses", [])
        if not _responses:
            print("No responses found.")
            return None
        return _responses
    except HttpError as e:
        print(f"An error occurred: {e}")
        return None


def get_form_questions(form_id: str) -> Optional[Dict[str, str]]:
    try:
        _form = service.forms().get(formId=form_id).execute()
        _questions = {}
        for item in _form.get("items", []):
            if "questionItem" in item and "question" in item["questionItem"]:
                _question_id = item["questionItem"]["question"].get("questionId")
                question_title = item["title"]
                if _question_id:
                    _questions[_question_id] = question_title
        return _questions
    except HttpError as e:
        print(f"An error occurred: {e}")
        return None


dictionary = json.load(
    open(
        "results/osh-eng-final-optimization/dictionary-w-100-20000-True-small-7.8261-ranked.json",
        "r",
        encoding="utf-8",
    )
)

filtered_scores = list()
discarded_scores = 0
filtered_almost_correct_scores = list()
almost_correct_stats = list()
questions = {}
words = set()
scores = defaultdict(list)
almost_correct_scores = defaultdict(list)

for _id in _ids:
    responses = get_form_responses(_id)
    questions.update(get_form_questions(_id))
    print(len(questions.keys()))
    for response in responses:
        for question_id, answer_dict in response.get("answers", {}).items():
            if question_id in questions:
                question_text = questions[question_id]
                current_word = re.search(r"'(?P<word>.+?)'", question_text).group(
                    "word"
                )
                words.add(current_word)
                if question_text.endswith(":"):
                    translations = dictionary.get(current_word, [])
                    for answer in answer_dict.get("textAnswers", {}).get("answers", []):
                        assert len(answer) <= 1
                        if not answer:
                            continue
                        elif answer.get("value") == "None of the above":
                            scores[current_word].append(-1)
                        else:
                            scores[current_word].append(
                                translations.index(answer.get("value")) + 1
                            )
                else:
                    for answer in answer_dict.get("textAnswers", {}).get("answers", []):
                        assert len(answer) <= 1
                        if not answer:
                            continue
                        else:
                            if answer.get("value") == "Yes":
                                almost_correct_scores[current_word].append(1)
                            elif answer.get("value") == "No":
                                almost_correct_scores[current_word].append(0)
                            else:
                                raise ValueError("Unexpected answer value")
for word, word_scores in scores.items():
    counter = Counter(word_scores)
    ordered_scores = iter(counter.most_common())
    for value, freq in ordered_scores:
        if freq > 1 and (
            not (next_score := next(ordered_scores, None)) or next_score[1] < freq
        ):
            filtered_scores.append(value)
            if almost_correct := almost_correct_scores.get(word):
                if (ratio := sum(almost_correct) / len(almost_correct)) == 0.5:
                    # No clear majority
                    filtered_almost_correct_scores.append(5)
                elif ratio > 0.5 and value == 1:
                    # The 1st translation was correct
                    filtered_almost_correct_scores.append(1)
                elif ratio > 0.5 and not value == 1:
                    # The first translation was almost correct, but originally classified as incorrect
                    print(word)
                    filtered_almost_correct_scores.append(2)
                elif ratio < 0.5 and value == 1:
                    # The first translation was marked correct, but not almost correct (annotation error)
                    filtered_almost_correct_scores.append(3)
                elif ratio < 0.5 and not value == 1:
                    # The first translation was not correct, also not almost correct
                    filtered_almost_correct_scores.append(4)
                else:
                    raise ValueError("Unexpected case")
            break
    else:
        if word in almost_correct_scores:
            filtered_almost_correct_scores.append(0)
        discarded_scores += 1


print(
    f"The dictionary scored {sum([1 / rank for rank in filtered_scores if rank > 0])/len(filtered_scores)} on the best translation task."
)
print(
    f"The dictionary scored {sum([score for score in filtered_scores if score == 1])/len(filtered_scores)} as P@1."
)
print(
    f"The dictionary scored {sum([1 for score in filtered_scores if 0 <= score <= 5])/len(filtered_scores)} as P@5."
)
print(
    f"The dictionary scored {sum([1 for score in filtered_scores if 0 <= score <= 10])/len(filtered_scores)} as P@10."
)
print(
    f"{len(filtered_scores)} scores were kept. {discarded_scores} scores were discarded."
)
counter = Counter(filtered_almost_correct_scores)
print(
    f"{counter[2]} translations were almost correct but not correct, "
    f"{counter[1]} were entirely correct, "
    f"{counter[3]} marked not almost correct but correct (error), "
    f"{counter[4]} marked incorrect and not almost correct, "
    f"{counter[5]} unmarked due to no majority and "
    f"{counter[0]} are unclear, due to no decision on the word."
)
print(f"{len(words - set(scores.keys()))} words were not answered in the top 10 list.")

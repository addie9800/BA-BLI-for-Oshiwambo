import json
import random

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# This file was created with the help of ChatGPT

# Path to the service account key file
SERVICE_ACCOUNT_FILE = "bachelor-thesis-448517-457f4122d888.json"

# Scopes required for the Google Forms API
SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/drive",
]

# Authenticate using the service account
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build("forms", "v1", credentials=credentials)
drive_service = build("drive", "v3", credentials=credentials)


def def_add_rights(file_id, email):
    permissions = drive_service.permissions().list(fileId=file_id).execute()
    permission_id = None

    for perm in permissions.get("permissions", []):
        if perm.get("emailAddress") == email:
            permission_id = perm["id"]
            break

    if not permission_id:
        new_permission = {
            "type": "user",
            "role": "writer",
            "emailAddress": email,
        }

        drive_service.permissions().create(
            fileId=file_id, body=new_permission
        ).execute()


# Load dictionary
dictionary = json.load(
    open(
        "results/osh-eng-final-optimization/dictionary-w-100-20000-True-small-7.8261-ranked.json",
        "r",
        encoding="utf-8",
    )
)

# Prepare form questions
dictionary_list = list(dictionary.items())
random.shuffle(dictionary_list)
questions = []
count = 0
# Generate questions
for word, translations in dictionary_list:
    count += 1
    # Question 1: Best translation
    questions.append(
        {
            "createItem": {
                "item": {
                    "title": f"Select the best translation for the word '{word}':",
                    "questionItem": {
                        "question": {
                            "choiceQuestion": {
                                "type": "RADIO",
                                "options": [
                                    {"value": t}
                                    for t in translations[: min(10, len(translations))]
                                ]
                                + [{"value": "None of the above"}],
                                "shuffle": False,
                            }
                        }
                    },
                },
                "location": {"index": 0},  # Insert at the start; adjust if needed
            }
        }
    )
    if count % 2 == 1:
        # Question 2: Almost accurate translation
        questions.append(
            {
                "createItem": {
                    "item": {
                        "title": f"Is '{word}' an almost accurate translation for '{translations[0]}'?",
                        "questionItem": {
                            "question": {
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [{"value": "Yes"}, {"value": "No"}],
                                    "shuffle": False,
                                }
                            }
                        },
                    },
                    "location": {"index": 0},  # Insert at the start; adjust if needed
                }
            }
        )


def create_form(part_number):
    # Create the form
    form_title = f"Translation Evaluation Survey"
    form = service.forms().create(body={"info": {"title": form_title}}).execute()
    form_id = form["formId"]
    # Prepare the batchUpdate request
    batch_update_body = {
        "requests": [
            {
                "updateFormInfo": {
                    "info": {
                        "title": f"Kunda to Part {part_number} of the Translation Evaluation Survey for my Thesis!",
                        "description": (
                            "In this survey, there are two types of questions. \n\n"
                            "You will be asked to select the best translation for a given word. "
                            "Please select the translation that you think is the best fit for the word. "
                            "In case you don't know the word or none of the translations are correct, "
                            "please select 'None of the above'. If two options are equally good, select the first "
                            "one. Please be strict in your judgement. What can happen is that some of the proposed "
                            "words are incomplete or a combination of two words. In that case, please select "
                            "'None of the above'. \n\n"
                            "The second type of question is a follow-up question to the first one. You will be asked"
                            " whether the selected word is an almost accurate translation for the first word. What "
                            "is meant is, that 'school' is translated with 'kofikola' instead of 'ofikola'. It would"
                            " be wrong for the first question, but in this case I would like you say yes.\n\n"
                            "Note that your progress is saved automatically. You can take a break anytime."
                        ),
                    },
                    "updateMask": "description,title",
                }
            }
        ]
    }
    try:
        service.forms().batchUpdate(formId=form_id, body=batch_update_body).execute()
        drive_service.files().update(
            fileId=form_id,
            body={"name": f"Translation Evaluation Survey - Part {part_number}"},
        ).execute()
    except HttpError as e:
        print(f"An error occurred: {e}")
        return -1
    # Output the form URL
    print(f"Form created successfully!")
    print(f"Form URL: https://docs.google.com/forms/d/{form_id}/edit")
    def_add_rights(form_id, "ad123br@gmail.com")
    return form_id


def add_batch(form_id, update_content):
    batch_update_body = {"requests": update_content}
    try:
        service.forms().batchUpdate(formId=form_id, body=batch_update_body).execute()
    except HttpError as e:
        print(f"An error occurred: {e}")
        return -1
    return 0


part_numbering = 1

current_id = create_form(part_numbering)
if current_id == -1:
    print("Failed to create form.")
    exit(1)

for i in range(100):
    update_success = add_batch(
        current_id,
        questions[
            i * (len(dictionary_list) // 100) : (i + 1) * (len(dictionary_list) // 100)
        ],
    )
    if update_success == -1:
        part_numbering += 1
        current_id = create_form(part_numbering)
        if (
            add_batch(
                current_id,
                questions[
                    i
                    * (len(dictionary_list) // 100) : (i + 1)
                    * (len(dictionary_list) // 100)
                ],
            )
            == -1
        ):
            print("Failed to create form.")
            exit(1)
add_batch(current_id, questions[100 * (len(dictionary_list) // 100) :])

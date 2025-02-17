import json
import re
from os import listdir
from typing import List, Optional

from fundus import Article, Crawler, PublisherCollection
from fundus.parser import ArticleBody
from tqdm import tqdm


def preprocess_sentence(sentence: str) -> Optional[str]:
    sentence = re.sub(r"(?i)^smses (for|of).*", "", sentence)
    sentence = re.sub("[^A-Za-z 0-9'öäüÖÄÜß]", "", sentence)
    sentence = re.sub(r"[0-9]+", "0", sentence)
    sentence = re.sub(r" +", " ", sentence)
    if sentence := sentence.lower().strip():
        return sentence + "\n"
    else:
        return None



def write_plaintext_to_file(filename: str, articles: List[Article]):
    with open(filename, "w", encoding="utf-8") as article_corpus_file:
        for article in tqdm(articles):
            if (title := article.get("title")) and (
                processed_title := preprocess_sentence(title)
            ):
                article_corpus_file.write(processed_title)
            body = ArticleBody.deserialize(article.get("body"))
            for sentence in re.split(r"[!.?]", str(body)):
                if processed_sentence := preprocess_sentence(sentence):
                    article_corpus_file.write(processed_sentence)


def crawl():
    crawler = Crawler(PublisherCollection.tz.DailyNewsTZ, restrict_sources_to=[])
    articles_in_english = list()
    articles_in_oshiwambo = list()
    try:
        for article in crawler.crawl(only_complete=False):
            if article.lang == "en":
                articles_in_english.append(article)
            else:
                articles_in_oshiwambo.append(article)
    except KeyboardInterrupt:
        pass
    finally:
        with open("articles_swa_v1.json", "w", encoding="utf-8") as file:
            file.write(
                json.dumps(
                    articles_in_oshiwambo,
                    default=lambda o: o.to_json(),
                    ensure_ascii=False,
                    indent=4,
                )
            )
        with open("articles_eng_tz_v1.json", "w", encoding="utf-8") as file:
            file.write(
                json.dumps(
                    articles_in_english,
                    default=lambda o: o.to_json(),
                    ensure_ascii=False,
                    indent=4,
                )
            )
        print(
            f"Amount of English articles: {len(articles_in_english)},"
            f" amount of Oshiwambo articles: {len(articles_in_oshiwambo)}"
        )


def to_corpus():
    eng_article_files = [
        file for file in listdir(".") if ("eng_tz" in file and "json" in file)
    ]
    swa_article_files = [
        file for file in listdir(".") if ("swa" in file and "json" in file)
    ]
    eng_articles = list()
    osh_articles = list()
    for file in eng_article_files:
        with open(file, "r", encoding="utf") as json_file:
            eng_articles.extend(json.load(json_file))
    for file in swa_article_files:
        with open(file, "r", encoding="utf") as json_file:
            osh_articles.extend(json.load(json_file))
    write_plaintext_to_file("articles_eng_tz.txt", eng_articles)
    write_plaintext_to_file("articles_swa.txt", osh_articles)

if __name__ == '__main__':
    crawl()
    to_corpus()

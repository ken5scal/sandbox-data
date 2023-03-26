import sys
import unicodedata
import requests
from bs4 import BeautifulSoup
from langdetect import detect
import openai
import os
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from uuid import uuid4, UUID
import argparse

@dataclass_json
@dataclass
class Section:
    sectionTitle: str = ""
    body: str = ""
    summary: str = ""

@dataclass_json
@dataclass
class ArticleSummary:
    uid: UUID = uuid4()
    title: str = ""
    url: str = ""
    language: str = ""
    summary: str = ""
    sections: list[Section] = field(default_factory=list)

def extract_sections2(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
    }
    response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')

    # ヘッダとフッタを削除する
    if soup.header:
        soup.header.decompose()
    if soup.footer:
        soup.footer.decompose()

        # 画像を削除する
    for img in soup.find_all('img'):
        img.decompose()

    # Remove script and style elements
    for script in soup(['script', 'style']):
        script.decompose()

    language = detect(soup.get_text())

    # Extract the title of the article
    title = soup.title.string if soup.title else "Unknown Title"
    title = unicodedata.normalize('NFKC', title)

    headings = ['h1', 'h2', 'h3']

    summaries = ArticleSummary()
    section = Section()

    for element in soup.find_all(['p'] + headings):
        text = element.text.replace('\n', '')
        if element.name in headings:
            if section.sectionTitle or section.body:
                summaries.sections.append(section)
                section = Section()
            section.sectionTitle = text
        else:
            section.body += text

    if section.sectionTitle or section.body:
        summaries.sections.append(section)

    summaries.title = str(title)
    summaries.url = url
    summaries.language = language
    
    return summaries

def summarize(content, twitterMode=False):
    # print(content)
    prompt = "\n\nsummarize for tech specialists"
    prompt += " with maximum of three bullet points with no more than 140 letters" if twitterMode else ""
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=content + prompt,
        temperature=0,
        max_tokens=144,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=1
    )
    return response.choices[0].text.replace('\n\n', '')


def summarize2(content):
    # print(content)
    prompt = "\n\nsummarize for tech specialists with maximum of three bullet points with no more than 140 letters."
    openai.api_key = openai.api_key = os.getenv("OPENAI_API_KEY")
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=content + prompt,
        temperature=0,
        max_tokens=140,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=1
    )
    return response.choices[0].text.replace('\n\n', '')

openai.api_key = openai.api_key = os.getenv("OPENAI_API_KEY")
parser = argparse.ArgumentParser(description="A simple script that takes two arguments")
parser.add_argument("url", type=str, help="URL (string)")
if __name__ == "__main__":
    args = parser.parse_args()

    # 抽出したいページのURLを入力
    # url = "https://unit42.paloaltonetworks.com/gobruteforcer-golang-botnet/"
    # url = "https://learn.microsoft.com/en-us/azure/active-directory/develop/custom-extension-overview"
    # url = "https://www.uptycs.com/blog/macstealer-command-and-control-c2-malware"
    # url = "https://happy-nap.hatenablog.com/entry/2022/08/17/210428"
    if not args.url:
        sys.exit("URL is required")

    result = extract_sections2(args.url)
    
    for section in result.sections:
        if section.body:
            section.summary = summarize(section.body)

    content = ""
    for section in result.sections:
        if section.summary:
            content += section.summary
        
    result.summary = summarize(content, True)
    print(result.summary)

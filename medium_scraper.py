import os
os.environ['TRANSFORMERS_CACHE'] = './transformers/cache/'

from functools import cache, lru_cache
import os.path
import re
import requests
from bs4 import BeautifulSoup
from wordcloud import WordCloud, STOPWORDS
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from keybert import KeyBERT
from operator import itemgetter
from transformers import pipeline
import streamlit as st
import matplotlib.pyplot as plt
import torch

print(torch.cuda.is_available())

st.set_option('deprecation.showPyplotGlobalUse', False)

def clean_text(text):
    cleaned_text = re.sub('[,\.!?:]', '', text)
    cleaned_text = cleaned_text.lower()
    nltk.download('punkt')
    nltk.download('stopwords')

    text_tokens = word_tokenize(cleaned_text)
    cleaned_text = [word for word in text_tokens if not word in stopwords.words()]
    cleaned_text = " ".join(cleaned_text)
    return cleaned_text

def generate_wordcloud(text):
    st.header("Word Cloud")
    wordcloud = WordCloud(background_color="white", stopwords=STOPWORDS, max_words=5000, contour_width=3, contour_color='steelblue').generate(text)
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.show()
    st.pyplot()

@cache
def scrape_article_text(url):
    response = requests.get(url, allow_redirects=True)
    page = response.content
    soup = BeautifulSoup(page, 'html.parser')
    sections = soup.find_all('section')

    article_text = ""
    for section in sections:
        paragraphs = section.find_all('p')
        for paragraph in paragraphs:
            article_text += paragraph.text + " "

        subs = section.find_all('h1')
        for sub in subs:
            article_text += "\n" + sub.text + "\n"
    
    return article_text

@lru_cache
@st.cache(allow_output_mutation=True)
def extract_keywords(text, nr_keywords, max_ngram_length):
    
    kw_model = KeyBERT()
    output = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, max_ngram_length), stop_words='english',
    use_maxsum=True, nr_candidates=20, top_n=nr_keywords)
    sorted_keywords = sorted(output, key=itemgetter(1), reverse=True)
    keywords = [pair[0] for pair in sorted_keywords]
    return keywords

def summarize(summary_percentage, text):
    @st.cache(allow_output_mutation=True)
    def load_summarizer():
        model = pipeline("summarization")
        return model

    summarizer = load_summarizer()

    tokenizer = summarizer.tokenizer
    input_tokenized = tokenizer.tokenize(text)
    text_parts = int(len(input_tokenized) / 512) + 1
    text_part_length = int(len(text) / text_parts)

    summary = ""
    for i in range(text_parts):
        text_part = text[i*text_part_length:(i+1)*text_part_length]
        max_length = int(len(tokenizer.tokenize(text_part)) * summary_percentage / 100)
        partial_summary = summarizer(text_part, max_length=max_length, return_text=True)
        summary += partial_summary[0]["summary_text"] + "\r\n"
    
    return summary

def analyze(parameters):
    if st.button("Start Analysis") and parameters["url"]:
        st.markdown("****")
        with st.spinner("Analyzing article.."):
            text = scrape_article_text(parameters["url"])
            generate_wordcloud(text)
            st.write("Keywords: " + str(extract_keywords(text, parameters["nr_keywords"], parameters["max_ngram_length"])))
            st.write(summarize(parameters["summary_percentage"], text))

def main():
    st.title("Medium article analyzer")
    st.markdown("****")
    st.header("Input analysis parameters")

    parameters = {}
    parameters["url"] = st.text_area("Enter the url of the article that you want to analyze here",height=10,help="paste the url of the article to be analyzed")
    parameters["summary_percentage"] = st.number_input("Enter the summary percentage from the original text", min_value=0, max_value=100, format="%d")
    parameters["nr_keywords"] = st.number_input("Enter the number of keywords to be extracted from the text", min_value=0, max_value=20, format="%d")
    parameters["max_ngram_length"] = st.number_input("Enter the maximum length of a keyword phrase", min_value=1, max_value=10, format="%d")

    analyze(parameters)

if __name__ == '__main__':
    main()
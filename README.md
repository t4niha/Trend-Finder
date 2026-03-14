**Text Preprocessing Module-**
**Overview**

This module preprocesses social media text data before it is used for further analysis, such as embeddings, clustering, or trend detection. The goal is to clean noisy text from Twitter/Reddit posts while preserving the semantic structure needed for NLP models.

**Features Implemented-**
!!Convert text to lowercase for normalization

!!Remove URLs using regular expressions and replace them with [removed]

!!Remove user mentions (@username)

!!Normalize hashtags by removing the # symbol while keeping the word

!!Remove emojis and special characters that may interfere with text processing

!!Normalize whitespace and remove extra spaces

!!Filter out posts with fewer than 10 characters to remove non-meaningful content

**Files**

1. preprocessing.py
Contains the main function named clean_post(text)
This function processes a single social media post and returns the cleaned version of the text.

2. clean_dataset.py
This script applies the preprocessing function to all JSON datasets in the data folder and generates cleaned versions of the datasets.

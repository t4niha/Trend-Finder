import json
import os
from preprocessing import clean_post

# folder containing datasets
data_folder = "../data"

# loop through all files in the data folder
for filename in os.listdir(data_folder):

    # process only original JSON files
    if filename.endswith(".json") and "_cleaned" not in filename:

        input_path = os.path.join(data_folder, filename)
        output_path = os.path.join(
            data_folder,
            filename.replace(".json", "_cleaned.json")
        )

        # load dataset
        with open(input_path, "r", encoding="utf-8") as f:
            posts = json.load(f)

        cleaned_posts = []

        for post in posts:
            cleaned_text = clean_post(post.get("text", ""))

            if cleaned_text:
                post["text"] = cleaned_text
                cleaned_posts.append(post)

        # save cleaned dataset
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_posts, f, indent=4, ensure_ascii=False)

        print(f"{filename} cleaned and saved as {filename.replace('.json','_cleaned.json')}")
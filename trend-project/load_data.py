import pandas as pd

print("STARTING...")

df = pd.read_csv("final_trendingtopics_reddit.csv")

print("DATA:")
print(df.head())

print("\nCOLUMNS:")
print(df.columns)

print("DONE")
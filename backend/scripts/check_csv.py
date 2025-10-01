# check_csv.py
import pandas as pd

df = pd.read_csv('../data/sample_questions/vocabulary.csv')
print("CSV Columns:")
print(df.columns.tolist())
print("\nFirst row:")
print(df.iloc[0])
print("\nExpected columns:")
expected = ['subject', 'question_id', 'question', 'option_a', 'option_b',
           'option_c', 'option_d', 'answer', 'topic', 'tier',
           'discrimination_a', 'difficulty_b', 'guessing_c']
print(expected)
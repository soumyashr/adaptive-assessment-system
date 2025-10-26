import pandas as pd
import os

print('Current working directory:', os.getcwd())

os.chdir('../data/sample_questions')
print('Current working directory:', os.getcwd())

# Read the Excel file
file_name = '../data/sample_questions/Complex_Numbers_MCQ.xlsx'
df = pd.read_excel('Complex_Numbers_MCQ.xlsx')

# Print all column names
print("Columns in your file:")
print(df.columns.tolist())

# Check for required columns
required = ['question', 'option_a', 'option_b', 'option_c', 'option_d', 'answer', 'tier', 'topic']
missing = [col for col in required if col not in df.columns]

if missing:
    print(f"\nMissing columns: {missing}")
else:
    print("\nAll required columns present!")

# Show first few rows
print("\nFirst 2 rows:")
print(df.head(2))
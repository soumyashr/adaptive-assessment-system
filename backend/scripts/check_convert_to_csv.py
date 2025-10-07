import pandas as pd

# update this
folder_name = "../data/sample_questions/"
file_name = 'complex_number.csv'

file_path = folder_name + file_name
# Try reading with different delimiters
try:
    df = pd.read_csv(file_path, delimiter=',')
    print("Comma worked")
except:
    try:
        df = pd.read_csv('complex_number.csv', delimiter=';')
        print("Semicolon worked")
    except:
        df = pd.read_csv('complex_number.csv', delimiter='\t')
        print("Tab worked")

# Check columns
print(df.columns.tolist())
print(df.head())

# Save properly
df.to_csv(folder_name+'complex_number_fixed.csv', index=False)
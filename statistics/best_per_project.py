import pandas as pd
import warnings
warnings.simplefilter(action='ignore')
# Loading data from the CSV file
df = pd.read_csv("algorithm_results.csv")

# Duration columns
time_columns = [
    'test_duration_ORIGINAL', 'test_duration_B', 
    'test_duration_C', 'test_duration_C+', 'test_duration_D'
]

# Removing commas (if present) and converting values to float
# for col in time_columns:
    # df[col] = df[col].str.replace(',', '').astype(float)

print('Total projects:', len(df))

# Filtering projects where durations are > 5 seconds for all executions
time_min = 5
filtered_data = df[(df[time_columns] > time_min).all(axis=1)]
print(f'Total projects with time > {time_min} seconds:', len(filtered_data))

# Initializing the count dictionary
counts = {col: 0 for col in time_columns[1:]}  # Exclude ORIGINAL
counts["draw"] = 0

# Processing each project
for _, row in filtered_data.iterrows():
    min_value = row[time_columns[1:]].min()  # Exclude ORIGINAL for comparison
    winners = row[time_columns[1:]][row[time_columns[1:]] == min_value].index.tolist()
    if len(winners) > 1:
        counts["draw"] += 1
    else:
        counts[winners[0]] += 1

# Calculating percentages
total_projects = len(filtered_data)
percentages = {
    col.split('_')[-1]: f'{round((value / total_projects) * 100, 1)}%' for col, value in counts.items()
}

# Raw results and percentages
print("Raw results by project:", counts)
print("Results by percentage:", percentages)

### Analysis with statistical significance ###
print('\nUsing statistical significance:')

# Calculating mean and standard deviation per project
mean_values = filtered_data[time_columns[1:]].mean(axis=1)  # Exclude ORIGINAL
std_dev_values = filtered_data[time_columns[1:]].std(axis=1)

# Determining which algorithm is significantly faster
is_faster = filtered_data[time_columns[1:]] < (mean_values - std_dev_values).values.reshape(-1, 1)

# Creating a column for the fastest algorithm or "None"
filtered_data['fastest'] = is_faster.apply(lambda row: row.idxmax() if row.any() else 'None', axis=1)

# Converting to simplified names
filtered_data['fastest'] = filtered_data['fastest'].replace({col: col.split('_')[-1] for col in time_columns[1:]})

# Counting occurrences per algorithm
result = filtered_data['fastest'].value_counts().to_dict()

# Ensuring all algorithms and "None" are represented in the result
all_algorithms = ['B', 'C', 'C+', 'D', 'None']
result = {alg: result.get(alg, 0) for alg in all_algorithms}

# Calculating percentages
total = sum(result.values())
results_percentage = {alg: f'{round(result.get(alg, 0) / total * 100, 2)}%' for alg in all_algorithms}

# Displaying the results
print("Result summary:", result)
print("Result percentages:", results_percentage)

# Listing projects where B, C, or C+ are the fastest, ordered by their ratio to D
print('Projects where B, C, or C+ are the fastest:')
fastest_than_d = filtered_data[filtered_data['fastest'].isin(['B', 'C', 'C+'])]
fastest_than_d['ratio'] = fastest_than_d['test_duration_D'] / fastest_than_d[['test_duration_B', 'test_duration_C', 'test_duration_C+']].min(axis=1)
fastest_than_d = fastest_than_d.sort_values('ratio', ascending=False)

for algo in ['B', 'C', 'C+']:
    print(f'\nAlgorithm {algo}:')
    for _, row in fastest_than_d[fastest_than_d['fastest'] == algo].iterrows():
        print(row['project'])

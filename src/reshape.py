import pandas as pd
from collections import defaultdict

def reshape_and_save_algorithm_data(df, algorithm_column, output_path='results.csv'):
    """
    Reshapes a DataFrame to have one row per project with algorithm-specific columns
    and saves the result to a CSV file.

    Parameters:
    -----------
    df : pandas.DataFrame
        Input DataFrame containing project executions for different algorithms
    algorithm_column : str
        Name of the column containing algorithm identifiers
    output_path : str
        Path where the CSV file will be saved (default: 'results.csv')

    Returns:
    --------
    pandas.DataFrame
        Reshaped DataFrame with one row per project and algorithm-specific columns
    """
    # List of columns we want to keep and transform
    columns_to_keep = [
        # 'time_instrumentation',
        # 'time_create_monitor',
        'test_duration',
        'total_monitors',
        'total_events'
    ]

    # Get unique algorithms
    algorithms = df[algorithm_column].unique()

    # Create a list to store DataFrames for each algorithm
    algorithm_dfs = []

    # Assuming the first column is the project identifier
    id_col = df.columns[0]

    for algo in algorithms:
        # Filter data for current algorithm
        algo_data = df[df[algorithm_column] == algo].copy()

        # Keep only the columns we want plus the identifier
        columns_to_use = [id_col] + columns_to_keep
        algo_data = algo_data[columns_to_use]

        # Add algorithm suffix to metric columns
        rename_dict = {col: f"{col}_{algo}" for col in columns_to_keep}
        algo_data = algo_data.rename(columns=rename_dict)

        algorithm_dfs.append(algo_data)

    # Merge all algorithm-specific DataFrames
    result = algorithm_dfs[0]
    for df_algo in algorithm_dfs[1:]:
        result = pd.merge(result, df_algo, on=id_col, how='outer')

    # remove the columns: total_monitors_ORIGINAL	total_events_ORIGINAL
    print(result.columns)
    result = result.drop(columns=['total_monitors_ORIGINAL', 'total_events_ORIGINAL'])

    #create a new column: best_other with the minimum of the columns test_duration_B test_duration_C and test_duration_C+
    result['best_other'] = result[['test_duration_B', 'test_duration_C', 'test_duration_C+']].min(axis=1)

    #create a new column: diff with the difference between the best_other and the test_duration_D
    result['diff'] = (result['test_duration_D'] - result['best_other']).round(5)

    output_columns = [
        'project', 'test_duration_ORIGINAL', 'test_duration_B', 'test_duration_C', 
        'test_duration_C+', 'test_duration_D', 'best_other', 'diff',
        'total_events_B', 'total_monitors_B', 'total_monitors_C', 'total_events_C',
        'total_monitors_C+', 'total_events_C+', 'total_monitors_D', 'total_events_D'
    ]
    r = result[output_columns]

    # Save to CSV
    r.to_csv(output_path, index=False)
    print(f"Results saved to {output_path}")

    #get infos on the columns of test_duration, How many times was each algorithm the fastest?
    # dict {algorithm: number of times it was the fastest}

    # create a column with the minimum of the test_duration columns
    result['best'] = result[['test_duration_B', 'test_duration_C', 'test_duration_C+', 'test_duration_D']].min(axis=1)
    fastest = {
        'B': 0,
        'C': 0,
        'C+': 0,
        'D': 0
    }
    for line in result.iterrows():
        column_name = 'test_duration_'
        min_value = line[1]['best']
        for algo in ['B', 'C', 'C+', 'D']:
            if line[1][column_name + algo] == min_value:
                fastest[algo] += 1
    print(fastest)

    return result

df = pd.read_csv("sanity-check-results.csv")
reshaped_df = reshape_and_save_algorithm_data(
    df=df,
    algorithm_column='algorithm',
    output_path='algorithm_results.csv'
)
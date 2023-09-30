import numpy as np
import osmnx as ox
import pandas as pd
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

import glob
import os
import geopandas as gpd



# define the column names as seen on the datasets for metrics
column_names = [
    "year", "jan", "flag_jan", "feb", "flag_feb", "mar", "flag_mar", 
    "apr", "flag_apr", "may", "flag_may", "jun", "flag_jun", "jul", 
    "flag_jul", "aug", "flag_aug", "sep", "flag_sep", "oct", "flag_oct", 
    "nov", "flag_nov", "dec", "flag_dec", "annual", "flag_annual", 
    "winter", "flag_winter", "spring", "flag_spring", "summer", "flag_summer", 
    "autumn", "flag_autumn"
]

# functions

def get_seasonal_measures(file_path, column_names):
    '''
    Function to read txt files and return a dataframe with values for 
    year, winter, spring, summer, autumn
    
    Input:
    file_path: str, relative path of the file to be read
    colum_names:list, the column headings to be given
    
    Returns:
    df_mod_filtered: df, pandas dataframe
    '''
    
    df = pd.read_csv(file_path, delimiter=',', skiprows = 4, header=None, encoding='latin-1')
    if len(df.columns) > 35:
        df = df.drop(df.columns[-1], axis=1)
    
    df.columns = column_names
    
    df_mod = df[['year', "winter", "flag_winter", "spring", "flag_spring", "summer", "flag_summer", "autumn", "flag_autumn"]]
    
    # Create a boolean mask to identify rows with any 'M' values for the seasons
    mask = (df_mod['flag_winter'] == 'M') | (df_mod['flag_spring'] == 'M') | (df_mod['flag_autumn'] == 'M') | (df_mod['flag_summer'] == 'M')
    # Use the boolean mask to filter the DataFrame and keep only rows where the condition is False
    df_mod_filtered = df_mod[~mask]
    df_mod_filtered = df_mod_filtered.drop(['flag_winter', 'flag_spring', 'flag_summer', 'flag_autumn'], axis = 1)
    
    return df_mod_filtered



def extract_metrics(metric_folder, column_names):
    '''
    Iterates over the specified folder, calls function to
    extract the metric, concatenates to a dataframes and saves in the clean folder
    
    Input:
    metric_folder: str, name of the metric folder under the raw folder
    column_names: list, the column headings to be given
    
    Return: None
    '''

    directory = f'data/raw/{metric_folder}'
    # list all the files
    files_list = os.listdir(directory)

    # Create an empty list to store the dataframes
    dataframes_list = []

    # iterate
    for file_name in files_list:
        # check if the fit is a text file
        if file_name.endswith('.txt'):
            # construct the full path to the file
            file_path = os.path.join(directory, file_name)

            # open the file
            with open(file_path, 'r') as file:
                # read the first line
                first_line = file.readline()

            # split the first line using comma delimiter
            parts = first_line.split(',')

            # Check if 'BC' is present after the second comma delimiter
            if len(parts)>2 and 'BC' in parts[2]:
                # do the data wrangling
                # print(f'Processing file: {file_name}')
                station_id = parts[0]
                station_name = parts[1]

                current_dataframe = get_seasonal_measures(file_path, column_names)
                current_dataframe = current_dataframe.assign(station_id = station_id)
                current_dataframe = current_dataframe.assign(station_name = station_name)

                if current_dataframe is not None:
                    dataframes_list.append(current_dataframe)

            else:
                # print(f'Skipping file: {file_name}')
                continue

    # Concatenate (vertically stack) all the dataframes in the list
    combined_dataframe = pd.concat(dataframes_list, ignore_index=True)

    # Export the combined dataframe to a CSV file
    combined_dataframe.to_csv(f'data/clean/{metric_folder}.csv', index=False)
    
    return

# Call the funcion to export the clean data
print("Extraction started")

print("Print extracting temperature data")
extract_metrics('temperature', column_names)
print("Print extracting precipitation data")
extract_metrics('precipitation', column_names)
print("Print extracting wind speed data")
extract_metrics('wind_speed', column_names)

print("Completed")

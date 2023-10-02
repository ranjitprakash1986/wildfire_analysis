# imports
import numpy as np
import osmnx as ox
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')
import glob

import os
import zipfile
import shutil

# functions

def fire_cause(value):
    '''
    returns the string category of the integer code of fire cause
    '''
    
    assert value in [0,1,2,3,4], 'fire cause is null or not between [0-4]'
    
    if value == 0:
        return 'Undefined'
    if value == 1:
        return 'Other'
    if value == 2:
        return 'Lightning'
    if value == 3:
        return 'Industry'
    if value == 4:
        return 'Human'
    else:
        return 'NA'

def burn_class(value):
    '''
    returns the string category of the burn extent
    '''
    
    assert value in [1,2,3,4], 'burn class is null or not between [1-4]'
    
    if value == 1:
        return 'Partial 0-25%'
    if value == 2:
        return 'Partial 25-50%'
    if value == 3:
        return 'Partial 50-75%'
    if value == 4:
        return 'Full 75-100%'
    else:
        return 'NA'
    

def yearly_wildfire_province(year, province):
    '''
    Return a dataframe with the wildfire details in the specified year and province
    
    Input:
        year: int, Year of interest
        province: Geopandas dataframe of the province of interest with 'EPSG:4326' projection
        
    Returns: 
        df: pandas dataframe, dataframe with cols: YEAR, NFIREID,FIRECAUS, BURNCLAS, AGENCY,POLY_HA, ADJ_HA, fire_area
    
    '''
    # Define the file pattern using a wildcard (*)
    file_pattern = f'data/raw/annual_wildfires/nbac_{year}_*'
    
    # Use glob to find files that match the pattern
    matching_files = glob.glob(file_pattern)
    
    if not matching_files:
        print(f"No files found for the pattern: {file_pattern}")
        return None
    
    if len(matching_files) > 1:
        print(f"Warning: More than one file matched the pattern. Continuing with the first file: {matching_files[0]}")
    
    file_to_read = matching_files[0] #this can be the zip file
    extract_dir = 'data/raw/annual_wildfires/temp'
    
    # Open the ZIP archive
    with zipfile.ZipFile(file_to_read, 'r') as zip_ref:
        # Extract all files from the ZIP archive to the specified directory
        zip_ref.extractall(extract_dir)
    

    # Read the file
    wildfires_yearfile = gpd.read_file(extract_dir)    

    # convert the wildfires gpd to angular units crs WGS 84 (good for locating places)
    wildfires_yearfile = wildfires_yearfile.to_crs("EPSG:4326")

    # Spatial join to get the wildfires that are contained within BC only
    joined_data = gpd.sjoin(wildfires_yearfile, province, how="inner", op='within')
    
    # get the centroid of the fires, latitude and longitude
    joined_data['centroid'] = joined_data.geometry.centroid
    joined_data['latitude'] = joined_data.centroid.y
    joined_data['longitude'] = joined_data.centroid.x



    # computing the area of the wildfires in BC
    joined_data_measure = joined_data.to_crs("EPSG:3347")
    joined_data_measure = joined_data_measure.assign(fire_area = (joined_data_measure.area) / 10000) # converted from sq.m to hectares

    # define a function to map columns to category types
    joined_data_measure['FIRECAUS'] = joined_data_measure['FIRECAUS'].map(fire_cause)
    joined_data_measure['BURNCLAS'] = joined_data_measure['BURNCLAS'].map(burn_class)
    joined_data_measure['YEAR'] = joined_data_measure['YEAR'].astype(int).astype(str)
    joined_data_measure['NFIREID'] = joined_data_measure['NFIREID'].astype(int).astype(str)
    
    # Create the dataframe    
    df = joined_data_measure.groupby(['YEAR', 'NFIREID', 'FIRECAUS', 'BURNCLAS', 'AGENCY']).agg({'POLY_HA': 'sum', 'ADJ_HA': 'sum', 'fire_area':'sum', 'latitude': 'min', 'longitude': 'min'}).reset_index(drop = False)
    
    # delete the extracted directory
    shutil.rmtree(extract_dir)
    
    return df


# Specify the province
prov_string = "British Columbia"

# Read and convert the wildfires gpd to angular units crs WGS 84 (good for locating places)
provinces = gpd.read_file("data/provinces")
provinces = provinces.to_crs("EPSG:4326") 
prov_gpd = provinces.query("PRENAME == @prov_string").copy()

# Create an empty list to store the dataframes
dataframes_list = []

# Loop through the years from 1986 to 2023
for year in range(1986, 2023):
    current_dataframe = yearly_wildfire_province(year, prov_gpd)
    if current_dataframe is not None:
        dataframes_list.append(current_dataframe)

# Concatenate (vertically stack) all the dataframes in the list
combined_dataframe = pd.concat(dataframes_list, ignore_index=True)

# Export the combined dataframe to a CSV file
combined_dataframe.to_csv('data/clean/wildfires.csv', index=False)
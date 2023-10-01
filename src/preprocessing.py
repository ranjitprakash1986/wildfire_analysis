# +
import IPython
import numpy as np
import osmnx as ox
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
plt.style.use('ggplot')
plt.rcParams.update({'font.size': 16, 'axes.labelweight': 'bold', 'figure.figsize': (6, 6), 'axes.edgecolor': '0.2'})

import warnings
warnings.filterwarnings('ignore')

import glob
import os

# -
import zipfile
import shutil


# ### Wildfires geopandas dataframe

filename = 'nbac_2015_r9_20210810'

zip_file_path = f'../data/raw/annual_wildfires/{filename}.zip'
extract_dir = f'../data/raw/annual_wildfires/{filename}'

# Open the ZIP archive
with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
    # Extract all files from the ZIP archive to the specified directory
    zip_ref.extractall(extract_dir)


# +
# geopandas dataframe of the wildfires

wildfires_2015 = gpd.read_file(extract_dir)
# -

wildfires_2015.columns

wildfires_2015.loc[:, "geometry"]



# convert the wildfires gpd to angular units crs WGS 84 (good for locating places)
wildfires_2015 = wildfires_2015.to_crs("EPSG:4326")

wildfires_2015.plot(edgecolor = "0.2", color = 'red', figsize=(10, 8))

# +
## shutil.rmtree(extract_dir)
# -

wildfires_2015[wildfires_2015['NFIREID']==1494]['geometry'].centroid.x

# ## British Columbia Province geopandas dataframe

provinces = gpd.read_file("../data/provinces")  # note that I point to the shapefile "directory" containg all the individual files
provinces = provinces.to_crs("EPSG:4326")    # I'll explain this later, I'm converting to a different coordinate reference system
provinces

province = "British Columbia"
bc = provinces.query("PRENAME == @province").copy()
bc

# +
import osmnx as ox

# bc = ox.geocode_to_gdf("British Columbia, Canada")
# bc.plot(edgecolor="0.2")
# bc = bc.to_crs("EPSG:4326")
# plt.title("British Columbia");
# -

# ### Spatial join

# +
# Spatial join to get the wildfires that are contained within BC only

joined_data = gpd.sjoin(wildfires_2015, bc, how="inner", op='within')
# -

joined_data.plot(edgecolor="0.2")

joined_data.columns

joined_data['centroid'] = joined_data.geometry.centroid
joined_data['latitude'] = joined_data.centroid.y
joined_data['longitude'] = joined_data.centroid.x


joined_data.head()

# computing the area of the wildfires in BC
joined_data_measure = joined_data.to_crs("EPSG:3347")

joined_data_measure = joined_data_measure.assign(fire_area = (joined_data_measure.area) / 10000) # converted from sq.m to hectares
joined_data_measure.head(5)

joined_data_measure[['POLY_HA', 'ADJ_HA', 'fire_area', 'latitude', 'longitude']] # the table values are in hectares, and the computed values are in square metres

joined_data_measure['latitude'].max()

joined_data_measure['longitude'].min()

# ### Display the wildfires on the BC province map

# +
ax = bc.plot(edgecolor = '0.2')
joined_data.plot(ax=ax, edgecolor="red", linewidth=0.5)
plt.title("Wildfires in BC in 2015");

df = (joined_data_measure.groupby(['YEAR', 'NFIREID', 'FIRECAUS', 'BURNCLAS', 'AGENCY'])).agg({'POLY_HA':'sum',
     'ADJ_HA': 'sum',
     'fire_area': 'sum',
     'latitude': 'min',
     'longitude': 'min'}).reset_index(drop = False)


# -

df[df['NFIREID']==1494]

# ### Sanity check of area units

# +
bc_measure = bc.to_crs("EPSG:3347")
bc_measure.area.sum()

# The answer is in sq. metres.
# -

# This is very close to the official 944,735 sq.km



# ### Writing a function

# Colunns in the shape file ( from pdf in 2022 folder)
#
# FID: Feature Identifier
# Shape: Feature Geometry
# Year: Year the fire burned
# NFIREID: unique assigned id to a specific fire event, used across province terrotory or park boundary
# BASRC: Id of the data provider
# Firemaps: data source or platform used to identify the burn
#     0: Undefined
#     1: Other sources not clearly defined
#     2: Field survey
#     3: Airborne platform
#     4: Aerial photograph
#     5: Satellite hotspots
#     6: Satellite Imagery other
#     7: Satellite Imagery - sPOT
#     8: Satellite Imagery - MODIS
#     9: Satellite Imagery - Landsat
#     10: Satellite Imagery - Sentinel
#     11: Satellite Imagery - Proba
# Firemapm: method used to delineate the burn polygon
# **Firecaus**: cause of the fire
#     0: Undefined
#     1: Other
#     2: Lightning     
#     3: Industry, forestry, oil and gas, agriculture
#     4: Human, non industrial activity (campfire , ATV etc)
# **Burnclas**: amount of burn, if not provided assumed to be fully burnt
#     1: partially burnt (1-25%)
#     2: partially burnt(25-50%)
#     3: partially burnt(50-75%)
#     4: Fully burnt(75-100%)
# Sdate: date of the first detected hotspots withinn the spatial extent of the fire event
# Edate: the date of the last detected hotspots withing the spatial extent of the fire event.
# afsdate: the fire start date reported by the agency
# afedate: the fire end date reported by the agency
# capdate: the acquistion date of the source data
# **polyha**: the total area of each fire polygon calculated in hectares using the canada albers equal area conic projection 
# adjha: the adjusted area of burn of each fire polygon calculated in hectares.
# adj_flag:
# **agency**: the jurisdiction (province, territory, park) where the fire burned. see pdf for specific details
# BTGID: sequential whole number identifier for the table
# version: version of the dataset
#
#
#
#     
#     
#

# +
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
# -



# +

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
    file_pattern = f'../data/raw/annual_wildfires/nbac_{year}_*'
    
    # Use glob to find files that match the pattern
    matching_files = glob.glob(file_pattern)
    
    if not matching_files:
        print(f"No files found for the pattern: {file_pattern}")
        return None
    
    if len(matching_files) > 1:
        print(f"Warning: More than one file matched the pattern. Continuing with the first file: {matching_files[0]}")
    
    file_to_read = matching_files[0]

    # Read the file
    wildfires_yearfile = gpd.read_file(file_to_read)    

    # convert the wildfires gpd to angular units crs WGS 84 (good for locating places)
    wildfires_yearfile = wildfires_yearfile.to_crs("EPSG:4326")

    # Spatial join to get the wildfires that are contained within BC only
    joined_data = gpd.sjoin(wildfires_yearfile, province, how="inner")


    # computing the area of the wildfires in BC
    joined_data_measure = joined_data.to_crs("EPSG:3347")
    joined_data_measure = joined_data_measure.assign(fire_area = (joined_data_measure.area) / 10000) # converted from sq.m to hectares

    # define a function to map columns to category types
    joined_data_measure['FIRECAUS'] = joined_data_measure['FIRECAUS'].map(fire_cause)
    joined_data_measure['BURNCLAS'] = joined_data_measure['BURNCLAS'].map(burn_class)
    joined_data_measure['YEAR'] = joined_data_measure['YEAR'].astype(int).astype(str)
    joined_data_measure['NFIREID'] = joined_data_measure['NFIREID'].astype(int).astype(str)
    
    # Create the dataframe
    df = joined_data_measure.groupby(['YEAR', 'NFIREID', 'FIRECAUS', 'BURNCLAS', 'AGENCY'])[['POLY_HA', 'ADJ_HA', 'fire_area']].agg('sum').reset_index(drop = False)
    
    return df
# -

prov_string = "British Columbia, Canada"

# +
prov_gpd = ox.geocode_to_gdf(prov_string)

# convert the wildfires gpd to angular units crs WGS 84 (good for locating places)
prov_gpd = prov_gpd.to_crs("EPSG:4326")

# +
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
combined_dataframe.to_csv('../data/clean/wildfires.csv', index=False)
# -





# +
# For each year, reads the shape file
# Extracts the polygons of wildfires that lie in BC only
# computes the area
# Group by NFIREID and compute the total fire area, Polygon Ha and Adjusted Ha. The same fire id may/maynot have duplicates [check if the values in firecause, burn clause, agency are same where duplicates]
# Use this dataframe and add the necessary columns - firecause, burn class, agency (province / territory etc)
# Writes the information to a csv, with year and area value
# -



# ### Extracting the mean temperature in each season in a province for each year

df = pd.read_csv('../data/raw/temperature/mm112FN0M.txt', delimiter=',', skiprows = 4, header=None)

df.columns

column_names = [
    "year", "jan", "flag_jan", "feb", "flag_feb", "mar", "flag_mar", 
    "apr", "flag_apr", "may", "flag_may", "jun", "flag_jun", "jul", 
    "flag_jul", "aug", "flag_aug", "sep", "flag_sep", "oct", "flag_oct", 
    "nov", "flag_nov", "dec", "flag_dec", "annual", "flag_annual", 
    "winter", "flag_winter", "spring", "flag_spring", "summer", "flag_summer", 
    "autumn", "flag_autumn"
]

df.columns = column_names

df.head()

df_mod = df[['year', "winter", "flag_winter", "spring", "flag_spring", "summer", "flag_summer", "autumn", "flag_autumn"]]

# Create a boolean mask to identify rows with all 'M' values
mask = (df_mod['flag_winter'] == 'M') | (df_mod['flag_spring'] == 'M') | (df_mod['flag_autumn'] == 'M') | (df_mod['flag_summer'] == 'M')


# Use the boolean mask to filter the DataFrame and keep only rows where the condition is False
df_mod_filtered = df_mod[~mask]

df_mod_filtered['year'].values

df_mod_filtered = df_mod_filtered.drop(['flag_winter', 'flag_spring', 'flag_summer', 'flag_autumn'], axis = 1)

df_mod_filtered.head()



# ### choosing to process only BC files
#
#

column_names = [
    "year", "jan", "flag_jan", "feb", "flag_feb", "mar", "flag_mar", 
    "apr", "flag_apr", "may", "flag_may", "jun", "flag_jun", "jul", 
    "flag_jul", "aug", "flag_aug", "sep", "flag_sep", "oct", "flag_oct", 
    "nov", "flag_nov", "dec", "flag_dec", "annual", "flag_annual", 
    "winter", "flag_winter", "spring", "flag_spring", "summer", "flag_summer", 
    "autumn", "flag_autumn"
]


def get_seasonal_measures(file_path, column_names):
    '''
    Function to read txt files and return a dataframe with values for 
    year, winter, spring, summer, autumn
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

    directory = f'../data/raw/{metric_folder}'
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
    combined_dataframe.to_csv(f'../data/clean/{metric_folder}.csv', index=False)
    
    return



extract_metrics('temperature', column_names)

extract_metrics('wind_speed', column_names)

extract_metrics('precipitation', column_names)



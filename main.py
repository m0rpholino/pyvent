import os.path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

"""
change 'my_filename' with the name of the file you want to calculate bins for (included the .xlsx format).
Files must be saved as excel sheets.
Set empty_rows to True if the file contains alternating empty rows, otherwise set it to False.
Set plot to True if you want to see plots at the end of processing.
Save should be set to True to save the file. Only set it to False to debug the code.
"""
# set filename
my_filename = r'buoni\pcf1.rf_1.iox.xlsx'
# boolean to detect empty rows
empty_rows = False  # boolean to detect empty rows
save = False  # boolean to save excel
plot = False  # boolean to show plots

"""
Definition of functions to clean the file and calculate averages over bins.
DO NOT MODIFY THIS
"""


def clean_df(filename):
    # skiprow function to open excel
    def skip_every_other_row(index):
        return index % 2 != 0

    # open file
    if empty_rows:
        whole_df = pd.read_excel(filename, skiprows=skip_every_other_row, index_col=0)
    else:
        whole_df = pd.read_excel(filename, index_col=0)

    # check cpu-date location
    cpu_date_check = whole_df[whole_df.eq('cpu-date').any(axis=1)]
    cpu_date_index = cpu_date_check.index[0]

    # reopen excel starting from cpu-date (time dataframe)
    if empty_rows:
        time_df = pd.read_excel(filename, skiprows=skip_every_other_row, index_col=0, header=cpu_date_index-1)
    else:
        time_df = pd.read_excel(filename, index_col=0, header=cpu_date_index - 1)

    # rename relevant columns
    time_df.rename(columns={'Unnamed: 5': 'run-events'}, inplace=True)  # FIXED PARAMETER HERE
    time_df.rename(columns={'Unnamed: 6': 'comments'}, inplace=True)  # FIXED PARAMETER HERE
    # slice df
    time_df = time_df.loc[:, :'comments']

    # check for the 'parameter' and 'unit' value and get their index
    parameter_check = whole_df[whole_df.eq('parameter').any(axis=1)]
    parameter_index = parameter_check.index[0]
    unit_check = whole_df[whole_df.eq('unit').any(axis=1)]

    # Initalize measures df: reopen file starting from parameter row
    if empty_rows:
        measure_df = pd.read_excel(filename, skiprows=skip_every_other_row, index_col=0, header=parameter_index-1)
    else:
        measure_df = pd.read_excel(filename, index_col=0, header=parameter_index-1)

    measure_df = measure_df.iloc[2:, 11:]  # drop the first two rows and keep only measures columns

    measure_df['AP'] = measure_df.apply(lambda row: (row['Te'] / row['RT'] + 1) if row['RT'] != 0 else 0, axis=1)  # calculate apneic pause

    # unpack parameters and units names
    parameters = measure_df.columns  # FIXED PARAMETER HERE
    units_array = unit_check.iloc[:, 11:].values.tolist()  # FIXED PARAMETER HERE
    units = [item for sublist in units_array for item in sublist]
    units = [unit if not pd.isna(unit) else '' for unit in units]
    units.append('')  # append empty string for AP unit

    # concatenate time and measures dfs
    new_columns = [parameter + '_' + unit for parameter, unit in zip(parameters, units)]
    new_columns_dict = {k: v for k, v in zip(parameters, new_columns)}
    adj_df = pd.concat([time_df, measure_df], axis=1)

    return adj_df, new_columns_dict


# calculate means for bins
def mean_bin(df: pd.DataFrame, baseline: int, bin_length: int, measures: list):
    # find period_start and period-stop entries
    period_start_check = df[df.eq('period-start').any(axis=1)]
    period_start_index = period_start_check.index
    period_stop_check = df[df.eq('period-stop ').any(axis=1)]
    period_stop_index = period_stop_check.index
    # print(period_start_index)
    # print(period_stop_index[-1])

    # make sure all relevant data is float
    df[measures] = df.loc[:period_stop_index[-1], measures].astype(float)
    for i in range(len(period_start_index)):  # iterate over period_start entries
        period_df = df.loc[period_start_index[i]+1:period_stop_index[i]-1, :]  # slice df from period_start to corresponding period_stop
        comment_check = period_df[period_df.eq('comment     ').any(axis=1)]  # check for the presence of comments
        comment_index = comment_check.index
        if comment_index.empty:  # if there are no comments, discard this period_start/period_stop section
            print('No comment found. Discarding data')
        else:  # if there are comments, group in bins
            # name = period_df.loc[comment_index[0], 'comments']
            print('Data for: ', df.loc[comment_index[0], 'comments'])
            start_point = (comment_index[0] - 1) - (baseline*6)  # set start point: 'baseline' minutes before comment
            baseline_df = period_df.loc[start_point:comment_index[0]-1, :]  # initialize a baseline df from start to comment
            injection_df = period_df.loc[comment_index[0]+1:period_stop_index[i], :]  # initialize an injection df from comment to period_stop
            end_point = round((period_stop_index[i] - comment_index[0]) / 6)  # explicitly define end point
            print(f'Baseline length in minutes: {baseline}')
            print(f'Injection length in minutes: {end_point}')
            window_size = bin_length * 6  # number of rows to be included in bin
            key = round(- baseline)  # variable that defines bin number
            print(f'startpoint: {key}')
            print(f'endpoint: {end_point}')
            bin_columns = np.arange(key, end_point, bin_length, dtype=int)  # initialize columns for df of bins
            print(bin_columns)
            bin_df = pd.DataFrame(data=None, index=measures, columns=bin_columns)  # initialize df of bins

            for j in range(start_point, comment_index[0]-1, window_size):  # iterate over baseline df from start point to comment
                print(f'Bin: {key}')
                print(baseline_df.loc[j:j+window_size, :])
                baseline_mean = baseline_df.loc[j:j+window_size, measures].mean(skipna=True)  # calculate mean over bin
                bin_df[key] = baseline_mean  # add the calculated mean to the bin df
                # print(bin_df)
                key += bin_length  # update bin number
            print('Finished baseline')

            for k in range(comment_index[0]+1, period_stop_index[i], window_size):  # iterate over injection df from comment to period_stop
                print(f'Bin: {key}')
                print(injection_df.loc[k:k+window_size, :])
                injection_mean = injection_df.loc[k:k+window_size, measures].mean(skipna=True)  # calculate mean over bin
                bin_df[key] = injection_mean  # add the calculated mean to the bin df
                bin_df = bin_df.copy()  # this ensures dataframe is not fragmented
                key += bin_length  # update bin number
            print('Finished injection')

            bin_df = bin_df.rename(index=my_new_columns_dict)  # rename parameters in bin df to include their unit

            for index in bin_df.index:
                bin_average = bin_df.loc[index, -baseline:-bin_length].mean()
                bin_df.loc[f'{index}_percent', :] = (bin_df.loc[index, :] / bin_average) * 100

            return bin_df

"""
Here you can set your own variables.
'relevant_measures' lets you specify the columns you are interested in.
These must be written in quotation marks and perfectly match the columns of the original file.
'my_baseline' lets you specify the length of baseline measurement in minutes. It must be an integer.
'my_bin_length' lets you specify the length of bins in minutes. It must be an integer.
"""

relevant_measures = ['Ti', 'TV', 'MV', 'PIF', 'AP']  # set relevant measures
my_baseline = 40  # set baseline
my_bin_length = 5  # set bin length

"""
Here we are calling functions to process the files according to the variables set and save them.
DO NOT MODIFY THIS
"""
cleaned_df, my_new_columns_dict = clean_df(my_filename)  # call function to clean df and get new columns name
my_bin_df = mean_bin(cleaned_df, my_baseline, my_bin_length, relevant_measures)  # call function to calculate averages

# save to excel
splitext = os.path.splitext(my_filename)[0]  # get the filename
new_name = splitext + f'_{my_bin_length}_min_bins.xlsx'  # specify new filename
if save:
    my_bin_df.to_excel(new_name)

"""
This is code to draw plots.
DO NOT MODIFY THIS
"""
# draw plots
if plot:
    my_bin_columns = my_bin_df.columns  # get bins
    for index in my_bin_df.index:  # iterate over measures
        baseline_average = my_bin_df.loc[index, -40:-5].mean()  # calculate the baseline average
        my_bin_df.loc[f'{index}_percent', :] = (my_bin_df.loc[index, :] / baseline_average)*100  # calculate the percent of baseline for each bin
        plt.figure(figsize=(8, 6))
        plt.scatter(my_bin_columns, my_bin_df.loc[f'{index}_percent', :])
        plt.plot(my_bin_columns, my_bin_df.loc[f'{index}_percent', :], color='red', linestyle='-', label='Lines')  # add line to connect data
        plt.axhline(y=100, color='black', linestyle='--')  # plot the 100% line
        plt.axvline(x=0, color='black', linestyle='-')
        plt.xticks(my_bin_columns, my_bin_columns)
        plt.title(f'{index}')
        plt.show()

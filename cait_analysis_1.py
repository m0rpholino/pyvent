from main import mean_bin
filenames = []

baseline = 40
bin_length = 5
relevant_measures = ['Ti', 'TV', 'MV', 'PIF', 'AP']
for file in filenames:
    mean_bin(file, baseline, bin_length, relevant_measures)
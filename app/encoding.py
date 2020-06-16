import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
import warnings

warnings.filterwarnings('ignore')


def add_noise(series, noise_level):
    return series * (1 + noise_level * np.random.randn(len(series)))


def target_encode(trn_series=None,  # training categorical feature as a pd.Series
                  tst_series=None,  # test categorical feature as a pd.Series
                  target=None,  # target data as a pd.Series
                  encoded_col=None,
                  min_samples_leaf=1,  # minimum samples to take category average into account
                  smoothing=1,  # smoothing effect to balance categorical average vs prior
                  noise_level=0):
    """
    Smoothing is computed like in the following paper by Daniele Micci-Barreca
    https://kaggle2.blob.core.windows.net/forum-message-attachments/225952/7441/high%20cardinality%20categoricals.pdf
    """
    assert len(trn_series) == len(target)
    assert trn_series.name == tst_series.name
    temp = pd.concat([trn_series, target], axis=1)
    print(temp)
    # Compute target mean
    averages = temp.groupby(by=trn_series.name)[target.name].agg(["mean", "count"])
    # Compute smoothing
    smoothing = 1 / (1 + np.exp(-(averages["count"] - min_samples_leaf) / smoothing))
    print('smoothing')
    print(smoothing)
    print(' ')
    print(type(smoothing))
    path = 'Lookup_Tables' + '\\' + encoded_col + '_lookup.csv'
    smoothing.to_csv(path, header=['values'])
    # Apply average function to all target data
    prior = target.mean()
    # The bigger the count the less full_avg is taken into account
    averages[target.name] = prior * (1 - smoothing) + averages["mean"] * smoothing
    averages.drop(["mean", "count"], axis=1, inplace=True)
    # Apply averages to trn and tst series
    ft_trn_series = pd.merge(
        trn_series.to_frame(trn_series.name),
        averages.reset_index().rename(columns={'index': target.name, target.name: 'average'}),
        on=trn_series.name,
        how='left')['average'].rename(trn_series.name + '_mean').fillna(prior)
    # pd.merge does not keep the index so restore it
    ft_trn_series.index = trn_series.index
    ft_tst_series = pd.merge(
        tst_series.to_frame(tst_series.name),
        averages.reset_index().rename(columns={'index': target.name, target.name: 'average'}),
        on=tst_series.name,
        how='left')['average'].rename(trn_series.name + '_mean').fillna(prior)
    # pd.merge does not keep the index so restore it
    ft_tst_series.index = tst_series.index
    return add_noise(ft_trn_series, noise_level), add_noise(ft_tst_series, noise_level)


def target_encode_main(train_test_series, train_data, test_data, train_x, test_x, train_y):
    # run target encode
    temp_train, temp_test = target_encode(train_x, test_x, train_y, train_test_series)

    # add encoded cols
    train_data[train_test_series + '_encoded'] = temp_train
    train_data = train_data.drop(columns=[train_test_series])
    test_data[train_test_series + '_encoded'] = temp_test
    test_data = test_data.drop(columns=[train_test_series])
    return train_data, test_data

# check if columns in train/test data match with each other
# If not, add the column and fill with 0

def column_check(data1, data2):
    # lists containing missing columns
    data1missing = data2.columns.difference(data1.columns).to_list()
    data2missing = data1.columns.difference(data2.columns).to_list()

    if len(data1missing) != 0:
        for col in data1missing:
            data1[col] = 0

    if len(data2missing) != 0:
        for col in data2missing:
            data2[col] = 0

    return data1, data2


def dummy(target_col, train_data, test_data):
    train_data = pd.get_dummies(train_data, columns=[target_col], drop_first=False)
    test_data = pd.get_dummies(test_data, columns=[target_col], drop_first=False)
    train_data, test_data = column_check(train_data, test_data)
    return train_data, test_data


def encoding(data, label):
    # drop all NAs if there is any
    data = data.dropna()

    # determine if all columns are numerical columns
    if data.apply(lambda s: pd.to_numeric(s, errors='coerce').notnull().all()).all():
        print('All columns are numerical. No need to encode any column')
        print('Finished!')
        return data

    else:
        if label == True:
            redo = "Y"
            count = 1
            # split data
            size = float(input('Enter the testing size: '))
            train_data, test_data = train_test_split(data, test_size=size)

            #############
            train_data = train_data.dropna()
            test_data = test_data.dropna()
            #############

            while redo.upper() == 'Y':
                print('Here are the columns from your dataset: \n')
                print(train_data.columns.to_list())
                encoded_col = input('Enter the column that you want to encode: ')
                try:
                    if data[encoded_col].nunique() < 5:
                        train_data, test_data = dummy(encoded_col, train_data, test_data)
                        # print and save backup
                        #print(train_data)
                        #print(test_data)
                        train_data.to_csv('Backup_train.csv', index = False)
                        test_data.to_csv('Backup_test.csv', index = False)
                        print('Columns in the current dataset: ')
                        print(train_data.columns.to_list())
                        # new columns
                        redo = input('Wanna encode a new column? Y/N')

                    else:
                        target_col = input('please enter your target column (Y column): ')  # a numeric column
                        train_x, test_x = train_data[encoded_col], test_data[encoded_col]
                        train_y, test_y = train_data[target_col], test_data[target_col]
                        train_data, test_data = target_encode_main(encoded_col, train_data, test_data, train_x, test_x,
                                                                   train_y)
                        # print and save backup
                        #print(train_data)
                        #print(test_data)
                        train_data.to_csv('Backup_train.csv', index = False)
                        test_data.to_csv('Backup_test.csv', index = False)
                        print('Columns in the current dataset: ')
                        print(train_data.columns.to_list())
                        # new columns
                        redo = input('Wanna encode a new column? Y/N')

                except KeyError as e:
                    print(' ')
                    print('Cannot find the column %s' % str(e))
                    print(' ')

                except:
                    print(' ')
                    print('There was an error raised when processing the data')
                    print(' ')

            # drop all other categorical columns
            for col1 in train_data:
                if str(train_data[col1].dtypes) != 'int64' and str(train_data[col1].dtypes) != 'float64' and str(
                        train_data[col1].dtypes) != 'uint8':
                    train_data = train_data.drop([col1], axis=1)

            for col2 in test_data:
                if str(test_data[col2].dtypes) != 'int64' and str(test_data[col2].dtypes) != 'float64' and str(
                        test_data[col2].dtypes) != 'uint8':
                    test_data = test_data.drop([col2], axis=1)

            print(data.dtypes)

            print('Encoding completed')
            print(train_data)
            print(' ')
            print(test_data)
            os.remove('Backup_train.csv')
            os.remove('Backup_test.csv')
            train_data.to_csv('train_data.csv', index = False)
            test_data.to_csv('test_data.csv', index = False)
            return train_data, test_data

        else:
            collist = []
            print(data.columns)
            redo = 'Y'
            while redo == 'Y':
                encoded_col = input('Enter the column that you want to encode: ')
                if data[encoded_col].nunique() < 5:
                    data = pd.get_dummies(data, columns=[encoded_col], drop_first=False)
                    # print and save backup
                    #print(train_data)
                    #print(test_data)
                    data.to_csv('Backup_encodededata.csv', index = False)

                    print('Columns in the current dataset: ')
                    print(data.columns.to_list())
                    # new columns
                    redo = input('Wanna encode a new column? Y/N')
                else:
                    print('This variable has more than 5 classes. Searching for lookup table')
                    path = 'Lookup_Tables' + '\\'+ encoded_col + '_lookup.csv'
                    #try:
                    lookup = pd.read_csv(path)
                    #try:
                    templist = data[encoded_col].unique()

                    print('Encoding the column...')
                    #print(data.shape)
                    for item in templist:
                        if item not in lookup[encoded_col].values:
                            #data = data.drop(data.loc[data[encoded_col] == item].index)
                            data.loc[data[encoded_col]==item, encoded_col] = 123456789

                    data[encoded_col + '_encoded'] = data[encoded_col].replace(lookup.iloc[:, 0].values,
                                                                               lookup.iloc[:, 1].values)
                    #print(data.shape)
                    data[encoded_col + '_encoded'] = data[encoded_col + '_encoded'].astype(float)
                    collist.append(encoded_col + '_encoded')
                    #print(collist)
                    data = data.drop(columns=[encoded_col])
                    print('Columns in the current dataset: ')
                    print(data.columns.to_list())
                    redo = input('Do you want to encode another column? (Y/N): ')
                    #except:
                    #print('There is a error raised when encoding the column.')
                    # except:
                    #     print('Lookup table not found')

            if len(collist) != 0:
                indexNames = data[data[collist[0]] == 123456789].index
                for i in collist[1:]:
                    indexNames.union(data[data[i] == 123456789].index)
                #print(data.shape)
                #print(indexNames)
                data.drop(indexNames, inplace=True)
                #print(data.shape)

                # drop all other categorical columns
                #print(data.dtypes)

            for col in data:
                if str(data[col].dtypes) != 'int64' and str(data[col].dtypes) != 'float64' and str(
                        data[col].dtypes) != 'uint8':
                    data = data.drop([col], axis=1)

            data.to_csv('data_for_prediction.csv', index = False)
            #print(data.dtypes)
            print('Finished')

            return data
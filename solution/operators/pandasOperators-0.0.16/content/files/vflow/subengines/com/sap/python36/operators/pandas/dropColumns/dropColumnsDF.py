import pandas as pd
import re
import json

EXAMPLE_ROWS = 5


def process(msg):

    prev_att = msg.attributes
    df = msg.body
    if not isinstance(df,pd.DataFrame) :
        raise TypeError('Message body does not contain a pandas DataFrame')

    att_dict = dict()
    att_dict['config'] = dict()

    #####################
    #  pd operations
    #####################
    att_dict['config']['drop_columns'] = api.config.drop_columns
    if api.config.drop_columns and not api.config.drop_columns.upper() == 'NONE':
        cols_str = api.config.drop_columns.replace(':','').replace('=','')
        # Test for NOT
        result = re.match(r'^([Nn][Oo][Tt])(.+)', cols_str)
        if result and result.group(1).upper() == 'NOT' :
            col_str = result.group(2)
            not_drop_cols = [x.strip().replace("'","").replace('"','') for x in col_str.split(',')]
            if len(not_drop_cols[0]) == 0 : # No list - reset index and drop all columns
                drop_cols = list(df.columns)
                df = df.reset_index()
            else :
                drop_cols = [ col for col in list(df.columns) if col not in not_drop_cols]
            df = df.drop(columns=drop_cols)
        else :
            result = re.match(r'^([Aa][Ll][Ll])', api.config.drop_columns)
            if result and result.group(1).upper() == 'ALL':
                drop_cols = list(df.columns)
                df = df.reset_index()
            else :
                drop_cols = [x.strip().replace("'","").replace('"','') for x in api.config.drop_columns.split(',')]
            df = df.drop(columns=drop_cols)

    att_dict['config']['rename_columns'] = api.config.rename_columns
    if api.config.rename_columns and not api.config.rename_columns.upper() == 'NONE':
        colmaps  = [x.strip() for x in api.config.rename_columns.split(',')]
        mapping = { cm.split(':')[0].strip().replace("'","").replace('"','') : \
                        cm.split(':')[1].strip().replace("'","").replace('"','')  for cm in colmaps}
        df.rename(columns = mapping, inplace=True)


    ##############################################
    #  final infos to attributes and info message
    ##############################################

    # df from body
    att_dict['operator'] = 'dropColumns' # name of operator
    att_dict['memory'] = df.memory_usage(deep=True).sum() / 1024 ** 2
    att_dict['name'] = prev_att['name']
    att_dict['columns'] = list(df.columns)
    att_dict['number_columns'] = len(att_dict['columns'])
    att_dict['number_columns'] = df.shape[1]
    att_dict['number_rows'] = df.shape[0]

    example_rows = EXAMPLE_ROWS if att_dict['number_rows'] > EXAMPLE_ROWS else att_dict['number_rows']
    for i in range(0,example_rows) :
        att_dict['row_'+str(i)] = str([ str(i)[:10].ljust(10) for i in df.iloc[i, :].tolist()])

    return api.Message(attributes=att_dict,body = df)



'''
Mock pipeline engine api to allow testing outside pipeline engine
'''
class test :
    BIGDATA = 1
    SIMPLE = 0
    SIMPLE_NOT = 2
    SIMPLE_ALL = 3
    SIMPLE_NOT_EMPTY = 4

test_scenario = test.SIMPLE

try:
    api
except NameError:
    class api:

        # input data - only used for isolated testing
        def set_test(test_scenario):
            if test_scenario == test.BIGDATA :
                df = pd.read_csv("/Users/madmax/big_data/test1.csv",sep=';')
                df.set_index(keys='index', inplace=True)

            else :
                df = pd.DataFrame(
                    {'icol': [1, 2, 3, 4, 5], 'xcol2': ['A', 'B', 'C', 'D', 'E'], \
                     'xcol3': ['K', 'L', 'M', 'N', 'O'],'xcol4': ['a1', 'a1', 'b1', 'b1', 'b1'], \
                     'xcol5': ['c1', 'c1', 'e1', 'e1', 'e1']})
                df.set_index(keys='icol', inplace=True)

            # input data
            att = {'format': 'pandas','name':'test'}

            return api.Message(attributes=att,body=df)

        # setting test config data
        def set_config (test_scenario) :
            if test_scenario == test.BIGDATA :
                api.config.drop_columns = 'location_id, supplier_id' # string
                api.rename_columns = ''
            elif  test_scenario == test.SIMPLE_NOT:
                api.config.drop_columns = 'NoT: xcol2, xcol3' # string
                api.rename_columns = ''
            elif  test_scenario == test.SIMPLE_NOT_EMPTY:
                api.config.drop_columns = 'NoT: ' # string
                api.rename_columns = ''
            elif test_scenario == test.SIMPLE_ALL:
                api.config.drop_columns = 'ALl'  # string
                api.rename_columns = ''
            else :
                api.config.drop_columns = 'xcol2, xcol3'  #
                api.config.rename_columns = "xcol4:N4 , 'xcol5': 'N5'"

        # definition of api.config - variable names should be same as in DI implementation
        class config:
            drop_columns = ''
            rename_columns = ''

        # fake definition of api.Message
        class Message:
            def __init__(self, body=None, attributes=""):
                self.body = body
                self.attributes = attributes

        # fake definition - can be used of asserting test results
        def send(port, msg):
            if isinstance(msg,str) :
                print(msg)
            else :
                print(msg.body)
            pass

        # fake definition - called by 'isolated'-test simulation
        def set_port_callback(port, callback):
            if isinstance(port,list) :
                port = str(port)
            print("Call \"" + callback.__name__ + "\"  messages port \"" + port + "\"..")
            # creates the message "send" to the inport based on the test
            msg= api.set_test(test_scenario)
            # sets the configuration based on the test
            api.set_config(test_scenario)
            # calls the "process" function
            callback(msg)

        def call(msg,config):
            api.config = config
            result = process(msg)
            return result, json.dumps(result.attributes, indent=4)

# gateway that gets the data from the inports and sends the result to the outports
def interface(msg):
    result = process(msg)
    api.send("outDataFrameMsg", result)
    info_str = json.dumps(result.attributes, indent=4)
    api.send("Info", info_str)


# Triggers the request for every message
api.set_port_callback("inDataFrameMsg", interface)

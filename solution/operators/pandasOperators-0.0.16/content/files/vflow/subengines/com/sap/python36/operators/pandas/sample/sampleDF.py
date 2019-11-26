import pandas as pd
import json

EXAMPLE_ROWS = 5

def process(msg):

    # test if body refers to a DataFrame type
    prev_att = msg.attributes
    df = msg.body
    if not isinstance(df,pd.DataFrame) :
        raise TypeError('Message body does not contain a pandas DataFrame')

    att_dict = dict()
    att_dict['config'] = dict()

    #####################
    #  pd operations
    #####################
    warning = ''

    # due to parametrization in ML Scenario Manager convert strings to integer
    if isinstance(api.config.sample_size, str):
        sample_size = int(api.config.sample_size)
    else:
        sample_size = api.config.sample_size
    if isinstance(api.config.random_state, str):
        random_state = int(api.config.random_state)
    else:
        random_state = api.config.random_state

    if not api.config.invariant_column or api.config.invariant_column.upper == 'NONE':
        # sample of whole df
        if len(df.index) < sample_size:
            warning = "Sample size larger than number of rows"
        else:
            df = df.sample(n=sample_size, random_state=random_state)
    else:
        # get the average number of records for each value of invariant
        s_col = api.config.invariant_column.strip()
        sc_df = df.groupby(s_col)[s_col].count()
        sample_size_invariant = int(sample_size / sc_df.mean())
        sample_size_invariant = 1 if sample_size_invariant == 0 else sample_size_invariant  # ensure minimum
        sc_df = sc_df.sample(n=sample_size_invariant, random_state=random_state).to_frame()
        sc_df.rename(columns={s_col: 'sum'}, inplace=True)
        # sample the df by merge 2 df
        df = pd.merge(df, sc_df, how='inner', right_index=True, left_on=s_col)
        df.drop(columns=['sum'], inplace=True)

    ##############################################
    #  final infos to attributes and info message
    ##############################################

    if df.empty :
        raise ValueError('DataFrame is empty')

    att_dict['operator'] = 'selectDataFrame'
    att_dict['name'] = prev_att['name']
    att_dict['memory'] = df.memory_usage(deep=True).sum() / 1024 ** 2
    att_dict['columns'] = str(list(df.columns))
    att_dict['number_columns'] = df.shape[1]
    att_dict['number_rows'] = df.shape[0]

    example_rows = EXAMPLE_ROWS if att_dict['number_rows'] > EXAMPLE_ROWS else att_dict['number_rows']
    for i in range(0,example_rows) :
        att_dict['row_'+str(i)] = str([ str(i)[:10].ljust(10) for i in df.iloc[i, :].tolist()])

    return  api.Message(attributes = att_dict,body=df)



'''
Mock pipeline engine api to allow testing outside pipeline engine
'''


class test:
    BIGDATA = 1
    SIMPLE = 0


test_scenario = test.BIGDATA

try:
    api
except NameError:
    class api:

        # input data - only used for isolated testing
        def set_test(test_scenario):
            if test_scenario == test.BIGDATA:
                df = pd.read_csv("/Users/d051079/OneDrive - SAP SE/Datahub-Dev/data/order_headers.csv", sep=';')
                df.set_index(keys='order_id', inplace=True)

            else:
                df = pd.DataFrame(
                    {'icol': [1, 2, 3, 4, 5], 'xcol2': ['A', 'B', 'C', 'D', 'E'], \
                     'xcol3': ['K', 'L', 'M', 'N', 'O'], 'xcol4': ['a1', 'a1', 'b1', 'b1', 'b1']})
                df.set_index(keys='icol', inplace=True)

            # input data
            att = {'format': 'pandas', 'name': 'test'}

            return api.Message(attributes=att, body=df)

        # setting test config data
        def set_config(test_scenario):
            if test_scenario == test.BIGDATA:
                api.config.random_state = "1"     # integer but provided as string
                api.config.sample_size = "2000"   # integer but provided as string
                api.config.invariant_column = 'shopper_id'
            else:  # test_scenario == test.SIMPLE:
                api.config.random_state = "1"  # integer but provided as string
                api.config.sample_size = "2"  # integer but provided as string
                api.config.invariant_column = 'xcol4'

        # definition of api.config - variable names should be same as in DI implementation
        class config:
            random_state = "1"  # integer but provided as string
            sample_size = "2"  # integer but provided as string
            invariant_column = ''  # string

        # fake definition of api.Message
        class Message:
            def __init__(self, body=None, attributes=""):
                self.body = body
                self.attributes = attributes

        # fake definition - can be used of asserting test results
        def send(port, msg):
            if isinstance(msg, str):
                print(msg)
                # pass
            else:
                print(msg.body)
            pass

        # fake definition - called by 'isolated'-test simulation
        def set_port_callback(port, callback):
            if isinstance(port, list):
                port = str(port)
            print("Call \"" + callback.__name__ + "\"  messages port \"" + port + "\"..")
            # creates the message "send" to the inport based on the test
            msg = api.set_test(test_scenario)
            # sets the configuration based on the test
            api.set_config(test_scenario)
            # calls the "process" function
            callback(msg)

        # called by 'integrated/pipeline-test simulation
        def test_call(msg):
            print('EXTERNAL CALL of module:' + __name__)
            api.set_config(test_scenario)
            result = process(msg)
            # because when called locally via this function, 'api.set_port_callback' and 'interface' are not called
            api.send("DataFrame", result)
            return result


# gateway that gets the data from the inports and sends the result to the outports
def interface(msg):
    result = process(msg)
    api.send("outDataFrameMsg", result)
    info_str = json.dumps(result.attributes, indent=4)
    api.send("Info", info_str)


# Triggers the request for every message
api.set_port_callback("inDataFrameMsg", interface)

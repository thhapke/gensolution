import sdi_utils.gensolution as gs
import sdi_utils.set_logging as slog
import sdi_utils.textfield_parser as tfp
import sdi_utils.tprogress as tp

import subprocess
import os
import sys
import pandas as pd
import traceback

try:
    api
except NameError:
    class api:

        queue = list()

        class Message:
            def __init__(self, body=None, attributes=""):
                self.body = body
                self.attributes = attributes

        def send(port, msg):
            if port == outports[1]['name']:
                api.queue.append(msg)

        class config:
            ## Meta data
            config_params = dict()
            version = '0.0.1'
            tags = {'pandas': '', 'sdi_utils': ''}
            operator_name = 'df_csv'
            operator_description = "df to csv"
            operator_description_long = "Creates a csv-formatted data passed to outport as message with the csv-string as body."
            add_readme = dict()
            add_readme[
                "References"] = r"""[pandas doc: to_csv](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_csv.html)"""

            debug_mode = True
            config_params['debug_mode'] = {'title': 'Debug mode',
                                           'description': 'Sending debug level information to log port',
                                           'type': 'boolean'}
            write_index = False
            config_params['write_index'] = {'title': 'Write Index', 'description': 'Write index or ignore it',
                                            'type': 'boolean'}

            separator = ','
            config_params['separator'] = {'title': 'Separator', 'description': 'Separator', 'type': 'string'}

            reset_index = False
            config_params['reset_index'] = {'title': 'Reset Index', 'description': 'Reset index or indices',
                                            'type': 'boolean'}

            rename = 'None'
            config_params['rename'] = {'title': 'Rename Columns', 'description': 'Rename columns (map)',
                                       'type': 'string'}

            select_columns = 'None'
            config_params['select_columns'] = {'title': 'Select Columns', 'description': 'Select columns.',
                                               'type': 'string'}
            datetime_conversion = False
            config_params['datetime_conversion'] = {'title': 'Datetime conversion (YYYY:MM:DD hh:mm:ss)',
                                            'description': 'Converting Datetime columns to format: YYYY:MM:DD hh:mm:ss.',
                                            'type': 'boolean'}

            bool_to_int = True
            config_params['bool_to_int'] = {'title': 'Convert boolean to int',
                                            'description': 'Converting boolean value to integer.',
                                            'type': 'boolean'}

            keyword_args = "None"
            config_params['keyword_args'] = {'title': 'Keyword Arguments',
                                             'description': 'Mapping of key-values passed as arguments \"to read_csv\"',
                                             'type': 'string'}

            sort_columns = False
            config_params['sort_columns'] = {'title': 'Sort Columns alphabetically',
                                             'description': 'Sort Columns alphabetically',
                                             'type': 'boolean'}


def process(msg):
    att_dict = msg.attributes

    att_dict['operator'] = 'df_csv'
    logger, log_stream = slog.set_logging(att_dict['operator'], loglevel=api.config.debug_mode)
    logger.info("Process started. Logging level: {}".format(logger.level))
    time_monitor = tp.progress()
    logger.debug('Attributes: {}'.format(str(msg.attributes)))

    df = msg.body

    if not isinstance(df, pd.DataFrame):
        logger.warning('Body of message is not of type DataFrame. No processing')
        logger.debug('Body value: {}'.format(msg.body))
        api.send(outports[0]['name'], log_stream.getvalue())
        api.send(outports[1]['name'], api.Message(attributes=att_dict, body=df))
        return 0
    if df.empty:
        logger.warning('DataFrame is empty. No processing')
        api.send(outports[0]['name'], log_stream.getvalue())
        api.send(outports[1]['name'], api.Message(attributes=att_dict, body=df))
        return 0

    logger.debug('DataFrame shape: {} - {}'.format(df.shape[0], df.shape[1]))

    data_str = ''

    try:
        # start custom process definition
        if api.config.reset_index:
            logger.debug('Reset Index')
            df = df.reset_index()

        rename_dict = tfp.read_dict(api.config.rename)
        if rename_dict:
            prev_columns = df.columns
            logger.debug('Renaming columns: {} ({} - {})'.format(rename_dict, prev_columns, df.columns))
            df.rename(columns=rename_dict, inplace=True)

        # Datetime
        if api.config.datetime_conversion :
            dt_cols = df.select_dtypes(include=['datetime64[ns, UTC]', 'datetime64[ns]', 'datetime64']).columns
            logger.debug('Datetime columns: {}'.format(dt_cols))
            for col in dt_cols:
                logger.debug('Column datetime conversion: {}'.format(col))
                df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')

        select_columns = tfp.read_list(api.config.select_columns)
        if select_columns:
            logger.debug('Column selection: {}'.format(select_columns))
            df = df[select_columns]

        if api.config.bool_to_int :
            bool_cols = df.select_dtypes(include='bool').columns
            logger.debug('Boolean columns: {}'.format(bool_cols))
            for bc in bool_cols:
                logger.debug('Boolean column conversion to int: {}'.format(bc))
                df[bc] = df[bc].astype(int)

        sep = api.config.separator
        if not sep:
            sep = ','
        logger.debug('to_csv - delimiter: {}'.format(sep))

        logger.debug('to_cvs - write_index: {}'.format(api.config.write_index))

        #df.dropna(inplace=True)
        logger.debug('DataFrame shape: {} - {}'.format(df.shape[0], df.shape[1]))

        # to ensure that the df has always the same order
        # when reading from DB this can sometimes change
        if api.config.sort_columns :
            df = df.reindex(sorted(df.columns), axis=1)

        kwargs = tfp.read_dict(text=api.config.keyword_args, map_sep='=')

        if not kwargs == None:
            logger.debug('to_csv - kwargs: {}'.format(kwargs))
            data_str = df.to_csv(sep=sep, index=api.config.write_index, **kwargs)
        else:
            logger.debug('to_csv - no kwargs.')
            data_str = df.to_csv(sep=sep, index=api.config.write_index)

    except Exception as e:
        logger.error(e)
        logger.debug('Process terminated with Error: {}'.format(time_monitor.elapsed_time()))
        api.send(outports[0]['name'], log_stream.getvalue())


    logger.debug('Process ended: {}'.format(time_monitor.elapsed_time()))
    logger.debug('Datastr: {}'.format(data_str))
    api.send(outports[0]['name'], log_stream.getvalue())
    api.send(outports[1]['name'], api.Message(attributes=att_dict, body=data_str))


inports = [{'name': 'data', 'type': 'message.DataFrame', "description": "Input data"}]
outports = [{'name': 'log', 'type': 'string', "description": "Logging data"}, \
            {'name': 'csv', 'type': 'message', "description": "Output data as csv"}]

#api.set_port_callback(inports[0]['name'], process)


def test_operator():

    api.config.write_index = False
    api.config.reset_index = True
    api.config.rename = 'icol:index, col3: column3'
    api.config.select_columns = "index, 'col 2', names, bool"
    api.config.bool_to_int = True
    api.config.sort_columns = True

    df = pd.DataFrame(
        {'icol': [1, 2, 3, 4, 5], 'col 2': ['2020-01-01', '2020-02-01', '2020-01-31', '2020-01-28', '2020-04-12'], \
         'col3': [100.0, 200.2, 300.4, 400, 500], 'names': ['Anna', 'Berta', 'Berta', 'Claire', 'Dora'], \
         'bool': [True, False, False, True, True]})
    df = df.set_index(keys=['icol'])
    df['col 2'] = pd.to_datetime(df['col 2'], format='%Y-%m-%d', utc=True)

    attributes = {'format': 'csv', 'name': 'DF_name', 'process_list': []}
    msg = api.Message(attributes=attributes, body=df)
    process(msg)

    str_list = [d.body for d in api.queue]
    str_str = '\n'.join(str_list)
    print(str_str)
    # out_file = '/Users/Shared/data/test/json_df.csv'
    # df.to_csv(out_file,index=False)

if __name__ == '__main__':
    #test_operator()
    if True:
        subprocess.run(["rm", '-r',
                        '/Users/d051079/OneDrive - SAP SE/GitHub/sdi_utils/solution/operators/sdi_utils_operators_' + api.config.version])
        gs.gensolution(os.path.realpath(__file__), api.config, inports, outports)
        solution_name = api.config.operator_name + '_' + api.config.version
        subprocess.run(["vctl", "solution", "bundle",
                        '/Users/d051079/OneDrive - SAP SE/GitHub/sdi_utils/solution/operators/sdi_utils_operators_' + api.config.version, \
                        "-t", solution_name])
        subprocess.run(["mv", solution_name + '.zip', '../../../solution/operators'])



import diutil.gensolution
import os

try:
    api
except NameError:
    class api:
        class config:

            ## Meta data
            tags = {'python36': ''}  # tags that helps to select the appropriate container
            operator_description = 'Custom Operator Template'
            version = "0.0.1"  # for creating the manifest.json
            config_params = dict()

            ## config paramter
            var1 = 'foo'
            config_params['var1'] = {'title': 'Variable1', 'description': 'Variable 1 for test', 'type': 'string'}
            var2 = 'bar'
            config_params['var2'] = {'title': 'Variable2', 'description': 'Variable 2 for test', 'type': 'string'}

        class Message:
            def __init__(self,body = None,attributes = ""):
                self.body = body
                self.attributes = attributes

        def send(port,msg) :
            print('Port: ', port)
            print('Attributes: ', msg.attributes)
            print('Body: ', str(msg.body))
            return msg

        def set_port_callback(port, callback) :
            default_msg = api.Message(attributes={'name':'doit'},body = 3)
            callback(default_msg)

        def call(config,msg):
            api.config = config
            return process(msg)


def process(msg):

    result = ''
    for i in range (0,msg.body) :
        result += str(i) + ':' + api.config.var1 + ' - ' + api.config.var2 + '    '
    return api.Message(attributes={'name':'concat','type':'str'},body=result)

inports = [{"name":"input","type":"message"}]
outports = [{"name":"output","type":"message"}]

def call_on_input(msg) :
    new_msg = process(msg)
    api.send(outports['name'],new_msg)

#api.set_port_callback('input', call_on_input)

def main() :
    print('Test: Default')
    api.set_port_callback(inports['name'], call_on_input)

    print('Test: config')
    config = api.config
    config.var1 = 'own foo'
    config.var12 = 'own bar'
    test_msg = api.Message(attributes={'name':'test1'},body =4)
    new_msg = api.call(config,test_msg)
    print('Attributes: ', new_msg.attributes)
    print('Body: ', str(new_msg.body))

    diutil.gensolution.gensolution(os.getcwd(), config, inports, outports, src_path=None, project_path = None, override_readme = False, tar = False))



if __name__ == '__main__':
    main()

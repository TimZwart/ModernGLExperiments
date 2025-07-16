import configparser
config = None
not_initialized = True

def init():
    print("init loadconfig")
    global config
    config = configparser.ConfigParser()
    if len (config.read('config.ini')) == 0:
        raise Exception("config.ini not found")

if not_initialized:
    init()
    not_initialized = False
def get_boolean_config(key):
    return config['GAME'].getboolean(key)

rotate_object = get_boolean_config('rotate_object')
relative_movement = get_boolean_config('relative_movement')

keybindings = {k: v.lower() for k, v in config['KEYBINDINGS'].items()}

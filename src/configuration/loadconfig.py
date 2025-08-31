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
if 'open_file' not in keybindings:
    keybindings['open_file'] = 'b'
if 'remove_backfaces' not in keybindings:
    keybindings['remove_backfaces'] = 'f10'
# Default keybinding for edge check if not provided
if 'check_edge' not in keybindings:
    keybindings['check_edge'] = 'f11'
# Default keybinding for extrusion if not provided
if 'extrude' not in keybindings:
    # Use a non-conflicting default key for extrusion
    keybindings['extrude'] = 'y'
mouse_rotation_button = int(config['KEYBINDINGS'].get('mouse_rotation_button', '2'))

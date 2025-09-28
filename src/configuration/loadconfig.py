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
# Shapes mode and shape entry defaults if not provided
if 'shapes_mode' not in keybindings:
    # Toggle shapes mode on/off
    keybindings['shapes_mode'] = 'm'
if 'shape_rectangle' not in keybindings:
    # Start rectangle entry (allowed to overlap with other keys; only active in shapes mode)
    keybindings['shape_rectangle'] = 'r'
if 'shape_ngon' not in keybindings:
    # Start regular n-gon entry (allowed to overlap with other keys; only active in shapes mode)
    keybindings['shape_ngon'] = 'g'
# Default Undo key (plain 'z'); Ctrl+Z is always supported in code regardless of this
if 'undo' not in keybindings:
    keybindings['undo'] = 'z'
# Default Cleanup Mode toggle if not provided
if 'cleanup_mode' not in keybindings:
    # Toggle cleanup mode on/off
    keybindings['cleanup_mode'] = 'u'
mouse_rotation_button = int(config['KEYBINDINGS'].get('mouse_rotation_button', '2'))

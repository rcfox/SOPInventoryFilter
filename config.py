import configparser

Config = configparser.ConfigParser(interpolation=None, delimiters=('=', ))
Config.read('config.ini')

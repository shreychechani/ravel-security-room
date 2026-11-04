import yaml


# FINDING 3: unsafe loader, but this module is never imported anywhere
def parse(text):
    return yaml.load(text, Loader=yaml.Loader)

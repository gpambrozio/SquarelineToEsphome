"""
YAML utilities for ESPHome format.
Custom classes and YAML configuration for ESPHome secrets, includes, and lambdas.
"""

import yaml


# Custom class to represent ESPHome secrets
class ESPHomeSecret:
    def __init__(self, secret_name):
        self.secret_name = secret_name


# Custom class to represent ESPHome includes
class ESPHomeInclude:
    def __init__(self, include_path):
        self.include_path = include_path


# Custom class to represent ESPHome lambdas
class ESPHomeLambda:
    def __init__(self, expression):
        self.expression = expression


# Custom representer for ESPHome secrets
def secret_representer(dumper, data):
    return dumper.represent_scalar("!secret", data.secret_name)


# Custom representer for ESPHome includes
def include_representer(dumper, data):
    return dumper.represent_scalar("!include", data.include_path)


# Custom representer for ESPHome lambdas
def lambda_representer(dumper, data):
    return dumper.represent_scalar("!lambda", data.expression)


# Register the representers
yaml.add_representer(ESPHomeSecret, secret_representer)
yaml.add_representer(ESPHomeInclude, include_representer)
yaml.add_representer(ESPHomeLambda, lambda_representer)


# Add custom constructor for !secret tags
def secret_constructor(loader, node):
    # Return an ESPHomeSecret object
    secret_name = loader.construct_scalar(node)
    return ESPHomeSecret(secret_name)


# Add custom constructor for !include tags
def include_constructor(loader, node):
    # Return an ESPHomeInclude object
    include_path = loader.construct_scalar(node)
    return ESPHomeInclude(include_path)


# Add custom constructor for !lambda tags
def lambda_constructor(loader, node):
    # Return an ESPHomeLambda object
    expression = loader.construct_scalar(node)
    return ESPHomeLambda(expression)


yaml.SafeLoader.add_constructor("!secret", secret_constructor)
yaml.SafeLoader.add_constructor("!include", include_constructor)
yaml.SafeLoader.add_constructor("!lambda", lambda_constructor)
